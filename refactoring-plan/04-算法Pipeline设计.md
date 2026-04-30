# SongHut 2.0 — 算法 Pipeline 设计

## 1. 设计哲学

### 1.1 原则

1. **纯函数优先**：每一阶段都是 `Input → Output` 的纯变换。无 I/O，无副作用。
2. **组合胜于继承**：Pipeline 由函数组合而成 (`pipe(a, f, g, h)`)，不是类继承链。
3. **显式依赖注入**：所有依赖（检测器、生成器）从外部传入，不在内部实例化。
4. **数据不可变**：每个阶段产生新的数据结构，不修改输入。
5. **类型即文档**：每个模块的 Protocol 定义即为完整接口契约。

### 1.2 Pipeline 概念模型

```
输入 (AudioBuffer)
  │
  ▼
┌─────────────────────────────────────────────┐
│               Pipeline 编排器                  │
│  (pipelines.py — 组合各阶段)                  │
│                                               │
│  stage_1 → stage_2 → stage_3 → ... → output  │
│    │          │          │                    │
│    ▼          ▼          ▼                    │
│  Pitch      Beat       Chord     . . .      │
│  Detector   Tracker    Detector              │
└─────────────────────────────────────────────┘
  │
  ▼
输出 (MidiOutput)
```

---

## 2. Pipeline 类型定义

### 2.1 核心 Pipeline 组合子

```python
# app/algorithms/pipeline.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, TypeVar

In = TypeVar("In")
Out = TypeVar("Out")

# 一个 Pipeline 阶段 = 转换函数
Stage = Callable[[In], Out]


class Pipeline(Generic[In, Out]):
    """函数式 Pipeline 组合器。将多个阶段链式组合。"""

    def __init__(self, stages: list[Stage]):
        self._stages = stages

    def run(self, input: In) -> Out:
        """顺序执行所有阶段。等价于: stage_n(...(stage_2(stage_1(input))))"""
        value = input
        for stage in self._stages:
            value = stage(value)
        return value

    def then(self, next_stage: Stage) -> "Pipeline":
        """返回新的 Pipeline：追加一个阶段。原 Pipeline 不变。"""
        return Pipeline([*self._stages, next_stage])


def pipe(value, *fns):
    """自由函数：value 穿过多函数"""
    for fn in fns:
        value = fn(value)
    return value
```

### 2.2 各阶段数据类型

```python
# ==== 全 pipeline 的数据变换路径 ====

# Step 0: 原始输入
AudioData = AudioBuffer

# Step 1 → 2 并行
PitchDetection = list[PitchFrame]
BeatInfo_result = BeatInfo

# Step 3: 合并音高和节拍 → 音符列表
NoteList = list[Note]

# Step 4: 主旋律 MIDI
MelodyTrack = MidiTrackData

# Step 5: 和弦
ChordList = list[Chord]

# Step 6: 伴奏轨道
AccompanimentTracks = list[MidiTrackData]

# Step 7: 最终输出
FinalOutput = MidiOutput
```

---

## 3. 各模块 Protocol 定义

### 3.1 音高检测 — Pitch Detector

```python
# app/algorithms/pitch/protocol.py
from typing import Protocol
from app.core.audio import AudioBuffer


class PitchDetector(Protocol):
    """音高检测器协议。
    职责：从原始音频中提取基频轨迹。
    纯函数：相同 audio → 相同结果。无副作用。"""

    def detect(self, audio: AudioBuffer) -> list[PitchFrame]:
        """检测音频中的基频。
        Args:
            audio: 单声道、16-bit、44.1kHz WAV 格式
        Returns:
            每 ~10ms 一帧的音高检测结果。
            升序按 time_sec 排列。"""
        ...

    @property
    def frame_hop_ms(self) -> float:
        """帧间隔 (ms)，决定返回的帧密度。"""
        ...

    @property
    def name(self) -> str:
        """检测器标识"""
        ...


class PitchPostProcessor(Protocol):
    """音高后处理：平滑、去噪、插值。在 detect() 之后调用。"""

    def smooth(self, frames: list[PitchFrame], window_ms: float = 50) -> list[PitchFrame]:
        """中值滤波平滑。去除瞬时杂音。"""
        ...

    def remove_unvoiced(self, frames: list[PitchFrame],
                        threshold: float = 0.5) -> list[PitchFrame]:
        """去除置信度低于阈值的帧，标记为 is_voiced=False"""
        ...

    def interpolate(self, frames: list[PitchFrame],
                    max_gap_ms: float = 100) -> list[PitchFrame]:
        """插值填充短间隙 (如极短的无声段)。"""
        ...
```

### 3.2 CREPE 实现

```python
# app/algorithms/pitch/crepe.py
import tensorflow as tf  # CREPE 需要 TF
import crepe
import numpy as np
from app.algorithms.pitch.protocol import PitchDetector


class CREPEDetector(PitchDetector):
    """CREPE 音高检测器 — 深度学习基频检测。
    精度: 2.5 cent, 帧间隔: ~10ms (10ms = 160 samples @ 16kHz)"""

    MODEL_SIZES = ("tiny", "small", "medium", "large", "full")

    def __init__(self, model_size: str = "tiny", batch_size: int = 512):
        if model_size not in self.MODEL_SIZES:
            raise ValueError(f"model_size must be one of {self.MODEL_SIZES}")
        self._model_size = model_size
        self._batch_size = batch_size
        # CREPE 模型延迟加载 (首次 detect 时初始化)
        self._model = None

    @property
    def frame_hop_ms(self) -> float:
        return 10.0

    @property
    def name(self) -> str:
        return f"CREPE-{self._model_size}"

    def detect(self, audio: AudioBuffer) -> list[PitchFrame]:
        audio_mono = audio.mono if audio.n_channels > 1 else audio

        # CREPE 要求 16kHz 输入
        if audio_mono.sample_rate != 16000:
            audio_mono = _resample(audio_mono, 16000)

        _, frequency, confidence, activation = crepe.predict(
            audio_mono.samples,
            audio_mono.sample_rate,
            model_capacity=self._model_size,
            batch_size=self._batch_size,
            viterbi=True,  # Viterbi 解码改善平滑性
        )

        return [
            PitchFrame(
                time_sec=float(i * self.frame_hop_ms / 1000),
                frequency_hz=float(freq),
                midi_note=float(hz_to_midi(freq)) if freq > 0 else 0.0,
                confidence=float(conf),
                is_voiced=conf > 0.5,
                amplitude=0.0,  # CREPE 未直接输出幅度
            )
            for i, (freq, conf) in enumerate(zip(frequency, confidence))
        ]


def hz_to_midi(freq: float) -> float:
    """频率转 MIDI 音高数 (连续值)"""
    if freq <= 0:
        return 0.0
    return 12 * np.log2(freq / 440.0) + 69.0


def _resample(audio: AudioBuffer, target_sr: int) -> AudioBuffer:
    """重采样到目标采样率"""
    import librosa
    samples = librosa.resample(
        audio.samples,
        orig_sr=audio.sample_rate,
        target_sr=target_sr,
    )
    return AudioBuffer(
        samples=samples,
        sample_rate=target_sr,
        n_channels=1,
    )
```

### 3.3 节拍跟踪 — Beat Tracker

```python
# app/algorithms/beat/protocol.py
from typing import Protocol
from app.core.audio import AudioBuffer


class BeatTracker(Protocol):
    """节拍跟踪器协议。
    职责：检测 BPM、拍点、强拍位置和拍号。
    纯函数。"""

    def detect(self, audio: AudioBuffer) -> BeatInfo:
        """检测节拍。
        Returns:
            BeatInfo: 包含 bpm、所有拍点、强拍点、推断的拍号。"""
        ...

    @property
    def name(self) -> str:
        ...
```

### 3.4 madmom 实现 (备选)

```python
# app/algorithms/beat/madmom.py
import madmom.features.beats as beats
import madmom.features.tempo as tempo


class MadmomBeatTracker(BeatTracker):
    """基于 RNN 的节拍检测。精度: ±2% BPM 误差。"""

    def __init__(self):
        self._tempo_processor = tempo.TempoEstimationProcessor(fps=100)
        self._beat_processor = beats.BeatTrackingProcessor(fps=100)
        self._rnn_processor = beats.RNNBeatProcessor()

    def detect(self, audio: AudioBuffer) -> BeatInfo:
        audio_mono = audio.mono

        # RNN 特征提取
        act = self._rnn_processor(audio_mono.samples)

        # 节拍跟踪
        beat_times = self._beat_processor(act)

        # 速度估计
        tempi = self._tempo_processor(act)

        bpm = float(tempi[0][0]) if len(tempi) > 0 else 120.0

        # 推断拍号 (简化：假设 4/4)
        return BeatInfo(
            bpm=bpm,
            beat_times=beat_times.tolist(),
            downbeat_times=[t for i, t in enumerate(beat_times) if i % 4 == 0],
            time_signature="4/4",
            beats_per_bar=4,
        )

    @property
    def name(self) -> str:
        return "madmom-RNN"
```

### 3.5 音符量化 — Quantizer

```python
# app/algorithms/midi/quantize.py
import numpy as np
from typing import Protocol


class Quantizer(Protocol):
    """音符量化器协议。
    职责：将连续音高轨迹 + 节拍信息 → 离散音符序列。
    纯函数。"""

    def quantize(self, pitches: list[PitchFrame], beats: BeatInfo) -> list[Note]:
        """
        Pipeline:
        1. 将 PitchFrame 按 beats 对齐到节拍网格
        2. 分段: 连续的 voiced 帧合并为一个 Note
        3. 量化音高到最近的半音 (MIDI 整数)
        4. 过滤: 去除超短音符 (< 30ms)
        """
        ...


class DefaultQuantizer(Quantizer):
    """基于节拍网格的启发式量化器。"""

    def quantize(self, pitches: list[PitchFrame], beats: BeatInfo) -> list[Note]:
        if not pitches:
            return []

        # 1. 分段 — 将连续 voiced 帧合并
        segments = self._segment(pitches)

        # 2. 量化 — 每段生成一个 Note
        notes = []
        for seg_start, seg_end in segments:
            seg_frames = pitches[seg_start:seg_end]
            onset_sec = seg_frames[0].time_sec
            duration = seg_frames[-1].time_sec + self._frame_dur(seg_frames) - onset_sec

            # 中值音高 → 最近半音
            median_midi = np.median([f.midi_note for f in seg_frames if f.is_voiced])
            pitch_midi = int(round(median_midi)) if not np.isnan(median_midi) else 60
            pitch_midi = max(0, min(127, pitch_midi))

            # 对齐到节拍网格
            onset_quantized, dur_quantized = self._snap_to_grid(
                onset_sec, duration, beats
            )

            beat_pos = self._calc_beat_position(onset_quantized, beats)
            measure = int(beat_pos // beats.beats_per_bar) if beats.beats_per_bar > 0 else 0

            note = Note(
                pitch_midi=pitch_midi,
                note_name=NoteName(pitch_midi % 12),
                octave=(pitch_midi // 12) - 1,
                onset_sec=onset_quantized,
                duration_sec=dur_quantized,
                velocity=self._calc_velocity(seg_frames),
                is_rest=False,
                beat_position=beat_pos,
                measure=measure,
            )
            notes.append(note)

        # 3. 填充小节间的休止 (避免间隙)
        notes = self._fill_rests(notes, beats)

        return notes

    def _segment(self, pitches: list[PitchFrame]) -> list[tuple[int, int]]:
        """将连续 is_voiced=True 的帧合并为段。"""
        segments = []
        start = None
        for i, frame in enumerate(pitches):
            if frame.is_voiced and start is None:
                start = i
            elif not frame.is_voiced and start is not None:
                if i - start > 3:  # 至少 4 帧 (40ms) 才算有效段
                    segments.append((start, i))
                start = None
        if start is not None and len(pitches) - start > 3:
            segments.append((start, len(pitches)))
        return segments

    def _snap_to_grid(self, onset: float, duration: float,
                      beats: BeatInfo) -> tuple[float, float]:
        """对齐到最近的节拍网格。"""
        if not beats.beat_times:
            return onset, duration

        beat_int = beats.beat_times[-1] / len(beats.beat_times)  # 平均拍间隔
        snapped_onset = min(beats.beat_times, key=lambda t: abs(t - onset))
        snapped_dur = max(beat_int * round(duration / beat_int), beat_int)
        return snapped_onset, snapped_dur

    def _calc_beat_position(self, onset: float, beats: BeatInfo) -> float:
        """计算在小节中的拍位置。"""
        if not beats.beat_times or onset < beats.beat_times[0]:
            return 0.0
        nearest_idx = min(range(len(beats.beat_times)),
                          key=lambda i: abs(beats.beat_times[i] - onset))
        return float(nearest_idx)

    def _calc_velocity(self, frames: list[PitchFrame]) -> int:
        """根据帧幅度中值计算力度。"""
        return 100  # 简化为固定力度，后续可改进

    def _fill_rests(self, notes: list[Note], beats: BeatInfo) -> list[Note]:
        """在音符间填充休止符，确保持续性。"""
        if len(notes) <= 1:
            return notes
        filled = [notes[0]]
        for i in range(1, len(notes)):
            gap = notes[i].onset_sec - filled[-1].onset_sec - filled[-1].duration_sec
            if gap > 0.05:  # > 50ms 的间隙
                rest = Note(
                    pitch_midi=0,
                    note_name=NoteName.C,
                    octave=0,
                    onset_sec=filled[-1].onset_sec + filled[-1].duration_sec,
                    duration_sec=gap,
                    velocity=0,
                    is_rest=True,
                    beat_position=0,
                    measure=0,
                )
                filled.append(rest)
            filled.append(notes[i])
        return filled

    @staticmethod
    def _frame_dur(frames: list[PitchFrame]) -> float:
        if len(frames) < 2:
            return 0.01
        return frames[1].time_sec - frames[0].time_sec
```

### 3.6 MIDI 生成器 — Midi Generator

```python
# app/algorithms/midi/generator.py
import io
import pretty_midi


class MidiGenerator:
    """音符列表 → MIDI 文件"""

    TICKS_PER_BEAT = 480

    def generate(self, notes: list[Note], instrument: int = 1,
                 track_name: str = "melody") -> MidiTrackData:
        """将音符列表转为 MIDI 轨道数据。"""
        midi_notes = []
        for note in notes:
            if note.is_rest:
                continue
            midi_note = pretty_midi.Note(
                velocity=note.velocity,
                pitch=note.pitch_midi,
                start=note.onset_sec,
                end=note.onset_sec + note.duration_sec,
            )
            midi_notes.append(midi_note)

        return MidiTrackData(
            name=track_name,
            instrument=instrument,
            notes=notes,  # 原始 Note 对象 (含乐理信息)
            is_drum=False,
        )

    def to_pretty_midi(self, output: MidiOutput) -> pretty_midi.PrettyMIDI:
        """将 MidiOutput 转为 pretty_midi 对象 (用于序列化)。"""
        pm = pretty_midi.PrettyMIDI(initial_tempo=output.tempo_bpm)

        for track_data in output.tracks:
            inst = pretty_midi.Instrument(
                program=9 if track_data.is_drum else track_data.instrument,
                is_drum=track_data.is_drum,
                name=track_data.name,
            )

            for note in track_data.notes:
                if note.is_rest:
                    continue
                inst.notes.append(pretty_midi.Note(
                    velocity=note.velocity,
                    pitch=note.pitch_midi,
                    start=note.onset_sec,
                    end=note.onset_sec + note.duration_sec,
                ))

            pm.instruments.append(inst)

        return pm

    def to_bytes(self, output: MidiOutput) -> bytes:
        """序列化为标准 MIDI 文件字节。"""
        pm = self.to_pretty_midi(output)
        buf = io.BytesIO()
        pm.write(buf)
        return buf.getvalue()
```

### 3.7 和弦分析 — Chord Detector

```python
# app/algorithms/chord/protocol.py
from typing import Protocol


class ChordDetector(Protocol):
    """和弦分析器协议。
    输入：量化后的音符序列。
    输出：和弦序列。
    可替换实现：规则引擎 / 深度学习 / 信号处理。"""

    def detect(self, notes: list[Note]) -> list[Chord]:
        """分析音符序列 → 和弦序列。
        通常每 1-2 个小节生成一个和弦。"""
        ...

    @property
    def name(self) -> str:
        ...


# app/algorithms/chord/rule_engine.py

class RuleBasedChordDetector(ChordDetector):
    """基于乐理规则的和弦检测器 (无需训练)。
    策略：
    1. 按拍网格切分窗口 (默认 2 拍一个和弦)
    2. 窗口内统计音高类分布
    3. 选择权重最高的音高类作为根音
    4. 匹配质量 (major/minor/dim/aug)"""

    BEATS_PER_CHORD = 2  # 每 2 拍一个和弦

    # 和弦模板: (半音程组合, 质量名)
    CHORD_TEMPLATES = {
        "maj":  (0, 4, 7),
        "min":  (0, 3, 7),
        "dim":  (0, 3, 6),
        "aug":  (0, 4, 8),
        "dom7": (0, 4, 7, 10),
        "maj7": (0, 4, 7, 11),
        "min7": (0, 3, 7, 10),
        "sus4": (0, 5, 7),
    }

    def detect(self, notes: list[Note]) -> list[Chord]:
        if not notes:
            return []

        # 1. 确定窗口边界
        total_beats = max((n.beat_position for n in notes), default=0)
        chords = []

        # 2. 按窗口分组
        for window_start in range(0, int(total_beats), self.BEATS_PER_CHORD):
            window_end = window_start + self.BEATS_PER_CHORD
            window_notes = [
                n for n in notes
                if window_start <= n.beat_position < window_end
                and not n.is_rest
            ]

            if not window_notes:
                continue

            # 3. 音高类直方图
            pitch_classes = [n.pitch_midi % 12 for n in window_notes]
            root = max(set(pitch_classes), key=pitch_classes.count)

            # 4. 匹配最佳质量
            quality = self._match_quality(pitch_classes, root)

            onset = window_notes[0].onset_sec
            duration = (window_end - window_start) * (60.0 / 120.0)  # 用 BPM 换算

            chord = Chord(
                root=NoteName(root),
                quality=quality,
                bass_note=NoteName(root),
                onset_sec=onset,
                duration_sec=duration,
                notes=tuple(sorted(set(pitch_classes))),
            )
            chords.append(chord)

        return chords

    def _match_quality(self, pitch_classes: list[int], root: int) -> str:
        """匹配和弦质量。用模板的最小二乘匹配。"""
        intervals = sorted(set((pc - root) % 12 for pc in pitch_classes))
        best_quality = "maj"
        best_score = float("inf")

        for quality, template in self.CHORD_TEMPLATES.items():
            score = sum(min(abs(iv - t) for t in template) for iv in intervals)
            if score < best_score:
                best_score = score
                best_quality = quality

        return best_quality

    @property
    def name(self) -> str:
        return "rule-engine"
```

---

## 4. 伴奏生成模块

### 4.1 鼓组生成

```python
# app/algorithms/accompany/drum.py

class DrumGenerator:
    """基于节拍的鼓组生成器。纯规则。"""

    # MIDI 鼓键映射 (GM Standard)
    KICK = 36          # 底鼓
    SNARE = 38         # 军鼓
    HIHAT_CLOSED = 42  # 闭镲
    HIHAT_OPEN = 46    # 开镲
    RIDE = 51           # 叮叮镲
    TOM_HIGH = 48       # 高音通通鼓
    TOM_MID = 45        # 中音通通鼓
    TOM_LOW = 41        # 低音通通鼓

    PATTERNS = {
        "rock": {               # 基本摇滚节奏
            "0": KICK,
            "0.5": SNARE,
            "1": KICK,
            "1.5": SNARE,
            "1.75": HIHAT_OPEN,  # 后十六
        },
        "pop": {                # 流行
            "0": KICK,
            "0.75": SNARE,
            "1": KICK + HIHAT_CLOSED,
            "1.5": SNARE,
        },
        "jazz": {               # 爵士摇摆 (swing feel)
            "0": RIDE,
            "0.33": HIHAT_CLOSED,
            "0.66": SNARE,
            "1": RIDE,
            "1.33": KICK,
            "1.66": SNARE,
        },
    }

    def __init__(self, default_pattern: str = "pop"):
        self._pattern = self.PATTERNS.get(default_pattern, self.PATTERNS["pop"])

    def generate(self, beats: BeatInfo, pattern: str | None = None) -> MidiTrackData:
        """根据节拍信息和样式生成鼓轨道。"""
        pattern_data = self.PATTERNS.get(pattern or "") or self._pattern

        notes = []
        beat_interval = 60.0 / beats.bpm  # 每拍秒数

        for i, beat_time in enumerate(beats.beat_times):
            for beat_offset_str, drum_note in pattern_data.items():
                offset = float(beat_offset_str)
                onset = beat_time + offset * beat_interval
                velocity = 100 if drum_note in (self.KICK, self.SNARE) else 80

                note = Note(
                    pitch_midi=drum_note,
                    note_name=NoteName.C,  # 鼓不关心音名
                    octave=0,
                    onset_sec=onset,
                    duration_sec=beat_interval * 0.3,
                    velocity=velocity,
                    is_rest=False,
                    beat_position=i + offset,
                    measure=int(i / beats.beats_per_bar),
                )
                notes.append(note)

        return MidiTrackData(
            name="drums",
            instrument=0,  # 鼓用 percussion channel
            notes=notes,
            is_drum=True,
        )
```

### 4.2 贝斯生成

```python
# app/algorithms/accompany/bass.py

class BassGenerator:
    """基于和弦进行的贝斯生成器。纯规则。"""

    def generate(self, chords: list[Chord], beats: BeatInfo) -> MidiTrackData:
        """每拍一个贝斯音符，根音跟随和弦。"""
        notes = []
        beat_interval = 60.0 / beats.bpm

        beats_per_chord = 0
        if chords and beats.beat_times:
            beats_per_chord = max(1, len(beats.beat_times) // len(chords))

        for chord in chords:
            # 计算和弦覆盖的拍子范围
            chord_start_beat = int(chord.onset_sec / beat_interval) if beat_interval > 0 else 0
            bass_root = int(chord.root) + 24  # 低两个八度

            for beat_offset in range(beats_per_chord):
                onset = chord.onset_sec + beat_offset * beat_interval

                note = Note(
                    pitch_midi=bass_root,
                    note_name=chord.root,
                    octave=2,
                    onset_sec=onset,
                    duration_sec=beat_interval * 0.9,
                    velocity=80,
                    is_rest=False,
                    beat_position=chord_start_beat + beat_offset,
                    measure=0,
                )
                notes.append(note)

        return MidiTrackData(
            name="bass",
            instrument=33,  # Electric Bass (finger)
            notes=notes,
            is_drum=False,
        )
```

### 4.3 和弦伴奏

```python
# app/algorithms/accompany/chord_accompany.py

class ChordAccompaniment:
    """基于和弦的伴奏生成器。支持柱式和琶音两种风格。"""

    def generate(self, chords: list[Chord], beats: BeatInfo,
                 style: str = "block") -> MidiTrackData:
        """生成和弦伴奏轨道。"""
        match style:
            case "block":
                return self._block_chords(chords, beats)
            case "arpeggio":
                return self._arpeggio_chords(chords, beats)
            case "both":
                return self._both(chords, beats)
            case _:
                return self._block_chords(chords, beats)

    def _block_chords(self, chords: list[Chord], beats: BeatInfo) -> MidiTrackData:
        """柱式和弦 — 三音/四音同时发声。"""
        notes = []
        for chord in chords:
            # 构建三和弦 (根音 + 三度 + 五度)
            root = int(chord.root)
            third = root + (3 if chord.quality in ("min", "min7") else 4)
            fifth = root + 7

            # 移调 MIDI 音域 (C3-C5)
            chord_pitches = [p + 36 for p in (root, third, fifth)]

            for pitch in chord_pitches:
                note = Note(
                    pitch_midi=pitch,
                    note_name=NoteName(pitch % 12),
                    octave=(pitch // 12) - 1,
                    onset_sec=chord.onset_sec,
                    duration_sec=chord.duration_sec,
                    velocity=70,
                    is_rest=False,
                    beat_position=0,
                    measure=0,
                )
                notes.append(note)

        return MidiTrackData(
            name="chords",
            instrument=1,  # Acoustic Grand Piano
            notes=notes,
            is_drum=False,
        )

    def _arpeggio_chords(self, chords: list[Chord], beats: BeatInfo) -> MidiTrackData:
        """琶音 — 音符依次出现。"""
        notes = []
        for chord in chords:
            root = int(chord.root)
            intervals = [0, 3 if chord.quality in ("min", "min7") else 4, 7]
            pitches = [p + 36 for p in intervals]

            beat_interval = 60.0 / beats.bpm if beats.bpm > 0 else 0.5
            arp_duration = chord.duration_sec / len(pitches)

            for i, pitch in enumerate(pitches):
                note = Note(
                    pitch_midi=pitch,
                    note_name=NoteName(pitch % 12),
                    octave=(pitch // 12) - 1,
                    onset_sec=chord.onset_sec + i * arp_duration,
                    duration_sec=arp_duration * 0.8,
                    velocity=65,
                    is_rest=False,
                    beat_position=0,
                    measure=0,
                )
                notes.append(note)

        return MidiTrackData(
            name="arpeggio",
            instrument=1,
            notes=notes,
            is_drum=False,
        )

    def _both(self, chords: list[Chord], beats: BeatInfo) -> MidiTrackData:
        """柱式和弦 + 琶音叠加 (需要两个轨道)。这里简化：返回柱式。"""
        return self._block_chords(chords, beats)
```

---

## 5. 乐谱生成模块

### 5.1 MIDI → MusicXML 转换

```python
# app/algorithms/score/converter.py
from xml.etree.ElementTree import Element, SubElement, tostring


class ScoreConverter:
    """将 MIDI 转换为 MusicXML。"""

    def midi_to_musicxml(self, midi_output: MidiOutput) -> str:
        """生成 MusicXML 字符串。"""
        root = Element("score-partwise", version="4.0")

        # part-list
        part_list = SubElement(root, "part-list")
        for i, track in enumerate(midi_output.tracks):
            score_part = SubElement(part_list, "score-part", id=f"P{i+1}")
            part_name = SubElement(score_part, "part-name")
            part_name.text = track.name

        # parts
        for i, track in enumerate(midi_output.tracks):
            part = SubElement(root, "part", id=f"P{i+1}")

            # 将音符按小节分组
            measures = self._group_by_measure(track.notes)
            for measure_idx, measure_notes in measures.items():
                measure = SubElement(part, "measure", number=str(measure_idx + 1))

                # attributes (只在第一小节和变化时)
                if measure_idx == 0:
                    attributes = SubElement(measure, "attributes")
                    divisions = SubElement(attributes, "divisions")
                    divisions.text = str(self.TICKS_PER_BEAT // 4)
                    time = SubElement(attributes, "time")
                    beats = SubElement(time, "beats")
                    beats.text = "4"
                    beat_type = SubElement(time, "beat-type")
                    beat_type.text = "4"
                    clef = SubElement(attributes, "clef")
                    sign = SubElement(clef, "sign")
                    sign.text = "G" if not track.is_drum else "percussion"
                    line = SubElement(clef, "line")
                    line.text = "2"

                # 音符
                for note in measure_notes:
                    self._add_note_element(measure, note)

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode")

    def _group_by_measure(self, notes: list[Note]) -> dict[int, list[Note]]:
        """按小节分组。"""
        measures: dict[int, list[Note]] = {}
        for note in notes:
            m = note.measure
            if m not in measures:
                measures[m] = []
            measures[m].append(note)
        return measures

    def _add_note_element(self, parent: Element, note: Note) -> None:
        """向 MusicXML measure 添加单个音符元素。"""
        note_elem = SubElement(parent, "note")

        if note.is_rest:
            rest = SubElement(note_elem, "rest")
        else:
            pitch = SubElement(note_elem, "pitch")
            step = SubElement(pitch, "step")
            step.text = ["C", "D", "E", "F", "G", "A", "B"][note.pitch_midi % 7]
            octave = SubElement(pitch, "octave")
            octave.text = str(note.octave)

            accidental = note.pitch_midi % 12 - [0, 2, 4, 5, 7, 9, 11][note.pitch_midi % 7]
            if accidental != 0:
                alter = SubElement(pitch, "alter")
                alter.text = str(accidental)

        duration = SubElement(note_elem, "duration")
        duration.text = str(int(note.duration_sec * self.TICKS_PER_BEAT / 4))

        # 力度
        dynamics = SubElement(note_elem, "dynamics")
        dynamics.text = str(note.velocity)

        # 时值类型
        type_elem = SubElement(note_elem, "type")
        type_elem.text = self._duration_to_type(note.duration_sec)

    @staticmethod
    def _duration_to_type(duration_sec: float) -> str:
        """秒数转 MusicXML 时值类型。"""
        # 简化: 假设 120 BPM
        beat_duration = 60.0 / 120  # 0.5 sec per quarter
        ratio = duration_sec / beat_duration
        if ratio >= 4:
            return "whole"
        elif ratio >= 2:
            return "half"
        elif ratio >= 1:
            return "quarter"
        elif ratio >= 0.5:
            return "eighth"
        elif ratio >= 0.25:
            return "16th"
        else:
            return "32nd"
```

---

## 6. Pipeline 编排器 — 完整组装

### 6.1 依赖注入容器

```python
# app/algorithms/container.py

class AlgorithmContainer:
    """算法组件容器 — 组装所有检测器和生成器。
    这是一个"配置对象"，而非 IoC 容器。
    所有依赖在初始化时注入，之后不变。"""

    def __init__(self, settings: Settings):
        self.pitch_detector = CREPEDetector(model_size=settings.crepe_model_size)
        self.beat_tracker = MadmomBeatTracker()
        self.quantizer = DefaultQuantizer()
        self.midi_generator = MidiGenerator()
        self.chord_detector = RuleBasedChordDetector()
        self.drum_generator = DrumGenerator()
        self.bass_generator = BassGenerator()
        self.chord_accompaniment = ChordAccompaniment()
        self.score_converter = ScoreConverter()

    def humming_to_melody(self, audio: AudioBuffer, params: MelodyParams) -> MidiOutput:
        """完整 pipeline"""
        return humming_to_melody(
            audio=audio,
            params=params,
            pitch_detector=self.pitch_detector,
            beat_tracker=self.beat_tracker,
            quantizer=self.quantizer,
            midi_generator=self.midi_generator,
            chord_detector=self.chord_detector,
            drum_gen=self.drum_generator,
            bass_gen=self.bass_generator,
            chord_accomp=self.chord_accompaniment,
        )

    def midi_to_score(self, midi_output: MidiOutput) -> str:
        """MIDI → MusicXML"""
        return self.score_converter.midi_to_musicxml(midi_output)


# 全局单例 (延迟初始化)
_container: AlgorithmContainer | None = None


def get_algorithm_container() -> AlgorithmContainer:
    global _container
    if _container is None:
        from app.core.config import settings
        _container = AlgorithmContainer(settings)
    return _container
```

---

## 7. 错误处理策略

### 7.1 Pipeline 阶段的错误

```python
# 每个阶段可能失败 — 使用 Result 包裹

def safe_pipeline(
    audio: AudioBuffer,
    params: MelodyParams,
    container: AlgorithmContainer,
) -> Result[MidiOutput, AppError]:
    """安全的 pipeline — 每个阶段捕获已知错误。"""
    try:
        pitches = container.pitch_detector.detect(audio)
        if not pitches or all(not p.is_voiced for p in pitches):
            return Err(AppError(
                code="PITCH_DETECTION_FAILED",
                message="未检测到有效音高。请确保录音包含清晰的旋律。",
            ))

        beats = container.beat_tracker.detect(audio)
        notes = container.quantizer.quantize(pitches, beats)
        output = humming_to_melody(audio, params, container.pitch_detector,
                                    container.beat_tracker, container.quantizer,
                                    container.midi_generator, container.chord_detector,
                                    container.drum_generator, container.bass_generator,
                                    container.chord_accompaniment)
        return Ok(output)

    except Exception as e:
        return Err(AppError(
            code="ALGORITHM_ERROR",
            message=f"算法执行失败: {e}",
        ))
```

### 7.2 输入约束

```python
def validate_audio(audio: AudioBuffer) -> Result[AudioBuffer, AppError]:
    """验证音频输入是否符合算法要求。"""
    errors = []
    if audio.n_channels == 0:
        errors.append("音频通道数为 0")
    if audio.duration_sec < 1.0:
        errors.append("音频过短 (至少 1 秒)")
    if audio.duration_sec > 600:
        errors.append("音频过长 (最长 10 分钟)")

     if errors:
        return Err(AppError(code="VALIDATION_ERROR",
                             message="; ".join(errors)))
    return Ok(audio)
```

---

## 8. 部署级设计：2 核 8GB 无 GPU Linux 约束

### 8.1 目标环境

| 维度 | 值 | 影响 |
|------|----|------|
| CPU | 2 核，无 GPU | 不能用 CUDA/cuDNN；深度学习模型必须 <10MB |
| 内存 | 8 GB | 算法处理常驻 ≤800MB；剩余留给 OS + DB + Worker |
| 操作系统 | Linux (华为云) | 路径分隔 `/`，不使用 `E:/data`；不依赖 Windows API |
| 网络 | 低带宽 | 模型下载仅首次。运行时零外网依赖 |
| 存储 | 40GB 云磁盘 | 算法缓存 ≤1GB；临时文件用完即删 |

### 8.2 依赖策略：主方案 + 降级方案

基于 2C8G 无 GPU 约束，所有检测器均需提供**轻量默认实现**。高级实现仅在依赖安装且模型已下载时才加载。

| 阶段 | 主方案（当前可用） | 降级方案（零额外依赖） | 升档方案（Python 3.12+） |
|------|-------------------|----------------------|------------------------|
| 音高检测 | `librosa.pyin` | 自带 librosa，零模型 | `torchcrepe` tiny (300KB) |
| 节拍跟踪 | `librosa.beat.beat_track` | 自带 librosa | `madmom` RNN (需 ~50MB 模型) |
| 音符量化 | `DefaultQuantizer` | 纯 Python 规则引擎 | — |
| MIDI 生成 | `pretty_midi` | 轻量纯 Python 库 | — |
| 和弦分析 | `RuleBasedChordDetector` | 纯规则，零训练 | — |
| 伴奏生成 | 规则模板 | 纯规则 | — |
| MIDI → WAV | `midi2audio` / `FluidSynth` | 需要 SF2 文件 | — |

**依赖清单（pyproject.toml algorithms 组）：**

```toml
[project.optional-dependencies]
algorithms = [
    "numpy>=1.26",
    "scipy>=1.14",
    "librosa>=0.10",          # pyin + beat_track + resample
    "pretty-midi>=0.3",       # MIDI I/O
    "music21>=9.3",            # MIDI → MusicXML (可选)
    "soundfile>=0.12",        # WAV 读写 (librosa 依赖)
]

# 升档 (Python 3.12+)
algorithms-plus = [
    "torchcrepe>=0.0.14",     # CREPE 音高检测 (300KB model)
    "madmom>=0.16",           # RNN 节拍跟踪 (~50MB model)
    "midi2audio>=0.1",        # MIDI → WAV 合成 (需要 FluidSynth)
]
```

### 8.3 性能预算

| 阶段 | 时间预算 10s 音频 | 时间预算 60s 音频 | 内存峰值 |
|------|-----------------|-----------------|---------|
| 加载 & 重采样 | <0.3s | <1s | ~15MB |
| pyin 音高检测 | ~2s | ~8s | ~80MB |
| beat_track | ~0.5s | ~2s | ~20MB |
| 量化 | <0.1s | <0.3s | ~5MB |
| MIDI 生成 | <0.1s | <0.1s | ~2MB |
| 和弦分析 | <0.2s | <0.5s | ~3MB |
| 伴奏生成 | <0.2s | <0.5s | ~3MB |
| **总计** | **~3.5s** | **~12.5s** | **~130MB** |

> 约束：单次算法调用不超过 30s（FastAPI gunicorn timeout 默认值）。
> 60s 音频 ≈ 普通哼唱一首歌的长度，12.5s 在 30s 安全线内。

### 8.4 内存管理

```python
# 处理后显式释放大对象
def humming_to_melody(audio: AudioBuffer, ...) -> MidiOutput:
    import gc

    frames = pitch_detector.detect(audio)
    beats = beat_tracker.detect(audio)
    notes = quantizer.quantize(frames, beats)

    # 释放中间态——量化后的 Note 规模远小于 PitchFrame
    del frames
    gc.collect()

    tracks = [midi_generator.generate(notes)]
    del notes
    ...

    return MidiOutput(tracks=tracks, tempo_bpm=beats.bpm)
```

### 8.5 递归依赖检测（优雅降级）

```python
# app/algorithms/pitch/registry.py
import importlib
from typing import Iterator

def available_detectors() -> Iterator[str]:
    """按精度降序，列出当前环境可用的 PitchDetector 实现名。
    eg: ['torchcrepe', 'pyin'] 或 ['pyin']"""
    yield "pyin"  # 始终可用 (librosa 是必须依赖)

    try:
        importlib.import_module("torchcrepe")
        yield "torchcrepe"
    except ImportError:
        pass

    try:
        importlib.import_module("parselmouth")
        yield "parselmouth"
    except ImportError:
        pass


def create_pitch_detector(name: str = "auto") -> PitchDetector:
    """工厂函数：根据名称或 auto 选择最佳可用检测器。"""
    if name == "auto":
        # 取第一个可用 (= 精度最高)
        name = next(available_detectors(), "pyin")

    match name:
        case "torchcrepe":
            from app.algorithms.pitch.torchcrepe_detector import TorchCREPEDetector
            return TorchCREPEDetector()
        case "pyin":
            from app.algorithms.pitch.pyin_detector import PyinDetector
            return PyinDetector()
        case _:
            raise ValueError(f"Unknown pitch detector: {name}")
```

### 8.6 文件路径约定（Linux）

```python
# 算法内部使用 POSIX 路径，不依赖 Windows `\\`
# 旧代码中 util.py 的 `getFilename()` 用 `\\` 分隔符 — 已废弃

from pathlib import Path

ALGORITHM_TEMP = Path("/tmp/songhut/algorithm")
ALGORITHM_TEMP.mkdir(parents=True, exist_ok=True)

def temp_midi_path(source_filename: str) -> str:
    """生成临时 MIDI 输出路径。例如 'recording.wav' → '/tmp/songhut/algorithm/recording.mid'"""
    stem = Path(source_filename).stem
    return str(ALGORITHM_TEMP / f"{stem}.mid")
```

### 8.7 测试数据策略

```python
# backend/app/algorithms/tests/conftest.py
import numpy as np
import pytest
from app.algorithms.audio import AudioBuffer

@pytest.fixture
def synthetic_scale() -> AudioBuffer:
    """合成 5 音上行音阶 (C4 D4 E4 F4 G4), 44100Hz mono。
    输出: 5 个音符, 各 0.5 秒, 静音间隙 0.05s。
    用于验证 pitch → quantize → MIDI 全链路。"""
    sr = 44100
    freqs = [261.63, 293.66, 329.63, 349.23, 392.00]
    note_dur = 0.5
    gap_dur = 0.05
    segments = []
    for f in freqs:
        t = np.linspace(0, note_dur, int(sr * note_dur), endpoint=False)
        segments.append(0.8 * np.sin(2 * np.pi * f * t))
        segments.append(np.zeros(int(sr * gap_dur)))
    return AudioBuffer(
        samples=np.concatenate(segments).astype(np.float32),
        sample_rate=sr,
        n_channels=1,
    )

@pytest.fixture
def synthetic_click_track() -> AudioBuffer:
    """合成 120BPM 节拍器音轨 (4/4, 8 小节)。
    用于验证 beat_track 输出 BPM ±5%。"""
    sr = 44100
    bpm = 120
    beat_interval = 60.0 / bpm
    n_beats = 32  # 8 bars × 4 beats
    duration = n_beats * beat_interval
    signal = np.zeros(int(sr * duration), dtype=np.float32)
    # 每拍一个短脉冲 (1kHz 正弦, 10ms)
    click = 0.8 * np.sin(2 * np.pi * 1000 * np.linspace(0, 0.01, int(sr * 0.01)))
    for i in range(n_beats):
        start = int(i * beat_interval * sr)
        end = start + len(click)
        if end < len(signal):
            signal[start:end] = click
    return AudioBuffer(samples=signal, sample_rate=sr, n_channels=1)

@pytest.fixture
def synthetic_cmajor_chord() -> AudioBuffer:
    """合成 C 大三和弦 (C4+E4+G4 同时响), 2 秒。
    用于验证和弦检测输出 Cmaj。"""
    sr = 44100
    t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
    signal = 0.5 * (
        np.sin(2 * np.pi * 261.63 * t) +
        np.sin(2 * np.pi * 329.63 * t) +
        np.sin(2 * np.pi * 392.00 * t)
    )
    return AudioBuffer(samples=signal.astype(np.float32), sample_rate=sr, n_channels=1)
```

### 8.8 算法验收标准

| 测试 | 输入 | 预期 | 容差 |
|------|------|------|------|
| `test_pitch_scale` | synthetic_scale (C-D-E-F-G) | 检测到 ≥4 个有效 note | 允许丢 1 个 |
| `test_pitch_frequency` | synthetic_scale | 每段中值频率与已知值误差 | <5% |
| `test_beat_bpm` | synthetic_click_track (120BPM) | 输出 BPM 118-122 | ±2 |
| `test_quantize_count` | synthetic_scale pitch frames | 输出 5 个 Note | ±1 |
| `test_quantize_pitch` | synthetic_scale | 输出 MIDI pitch [60,62,64,65,67] 顺序 | 可容忍 ±1 半音 |
| `test_midi_valid` | 量化后的 Note[] | pretty_midi 可解析 | 0 错误 |
| `test_midi_track_count` | 无伴奏 | 1 个 track (melody) | ≥1 |
| `test_midi_track_count` | 加鼓+贝斯 | ≥3 个 tracks | ≥3 |
| `test_pipeline_e2e` | synthetic WAV → pipeline | 输出合法 MIDI 且 BPM 100-140 | 0 错误 |
| `test_chord_cmajor` | synthetic_cmajor_chord → chord detect | 输出 "Cmaj" | 精确匹配 |
| `test_memory` | 60s WAV → pipeline 单次执行 | 内存增长 <200MB | 0 内存泄漏 |

---

## 9. 实施顺序

| Phase | 内容 | 可验证 |
|-------|------|--------|
| **A** | `algorithms/audio.py` — AudioBuffer + load/resample/validate | synthetic_scale fixture |
| **B** | `algorithms/pitch/pyin_detector.py` — libsora.pyin 实现 | test_pitch_scale |
| **C** | `algorithms/beat/librosa_beat.py` — beat_track 实现 | test_beat_bpm |
| **D** | `algorithms/midi/quantize.py` — 量化器 + snap_tolerance | test_quantize_* |
| **E** | `algorithms/midi/generator.py` — pretty_midi 包装 | test_midi_* |
| **F** | `algorithms/pipeline.py` — 全链路编排 | test_pipeline_e2e |
| **G** | `algorithms/chord/` — 规则引擎 | test_chord_cmajor |
| **H** | `algorithms/accompany/` — 鼓/贝斯/和弦伴奏 | test_midi_track_count |
| **I** | `algorithms/score/converter.py` — MIDI → MusicXML | synthetic import 可解析 |
| **J** | `algorithms/container.py` — 依赖组装 + 注册表 | 跨检测器切换测 |

每个 Phase 的输出都是一个可运行的 Python 模块 + 一个 pytest 测试文件。
```
