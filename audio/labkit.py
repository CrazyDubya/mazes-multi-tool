import numpy as np
import soundfile as sf
import librosa
import pyrubberband as pyrb
from scipy.io import wavfile
from scipy.signal import lfilter, butter
from pydub import AudioSegment
from pydub.playback import play
import pyworld as pw
import joblib
from abc import ABC, abstractmethod


class VoiceEffect(ABC):
    @abstractmethod
    def apply(self, audio, sr):
        pass


class ReverbEffect(VoiceEffect):
    def apply(self, audio, sr):
        reverb_time = 0.1
        delay = int(sr * 0.1)
        decay = np.exp(-6.9 * np.arange(int(reverb_time * sr)) / (reverb_time * sr))
        impulse_response = np.zeros(int(reverb_time * sr))
        impulse_response[delay:delay + len(decay)] = decay
        return np.convolve(audio, impulse_response, mode='full')[:len(audio)]


class CompressionEffect(VoiceEffect):
    def apply(self, audio, sr):
        threshold = 0.1
        ratio = 4.0
        audio_compressed = np.copy(audio)
        mask = abs(audio) > threshold
        audio_compressed[mask] = threshold + (abs(audio[mask]) - threshold) / ratio * np.sign(audio[mask])
        return audio_compressed


class AudioProcessor:
    def __init__(self):
        self.effects = []

    def add_effect(self, effect):
        self.effects.append(effect)

    def process(self, audio, sr):
        for effect in self.effects:
            audio = effect.apply(audio, sr)
        return audio


class VoiceModifier:
    def __init__(self):
        self.audio_processor = AudioProcessor()
        self.emotion_classifier = joblib.load('emotion_classifier.joblib')  # Pretend this exists

    def load_audio(self, file_path):
        return librosa.load(file_path, sr=None)

    def save_audio(self, audio, sr, file_path):
        sf.write(file_path, audio, sr)

    def play_audio(self, audio, sr):
        audio_segment = AudioSegment(
            audio.tobytes(),
            frame_rate=sr,
            sample_width=audio.dtype.itemsize,
            channels=1
        )
        play(audio_segment)

    def pitch_shift(self, audio, sr, n_steps):
        return pyrb.pitch_shift(audio, sr, n_steps)

    def time_stretch(self, audio, sr, rate):
        return pyrb.time_stretch(audio, sr, rate)

    def formant_shift(self, audio, sr, shift_factor):
        f0, sp, ap = pw.wav2world(audio.astype(np.double), sr)
        sp_stretched = np.zeros_like(sp)
        for f in range(sp.shape[1]):
            sp_stretched[:, f] = np.interp(np.arange(0, sp.shape[0], shift_factor),
                                           np.arange(0, sp.shape[0]), sp[:, f])
        return pw.synthesize(f0, sp_stretched, ap, sr)

    def apply_emotion(self, audio, sr, emotion):
        params = {
            "happy": {"pitch": 2, "speed": 1.1, "formant": 1.1, "jitter": 0.01},
            "sad": {"pitch": -2, "speed": 0.9, "formant": 0.9, "jitter": 0.005},
            # Add more emotions and parameters as needed
        }
        p = params.get(emotion, params["neutral"])

        audio = self.pitch_shift(audio, sr, p["pitch"])
        audio = self.time_stretch(audio, sr, p["speed"])
        audio = self.formant_shift(audio, sr, p["formant"])

        # Apply jitter
        jitter = np.random.normal(0, p["jitter"], len(audio))
        audio += jitter

        return audio

    def apply_ssml(self, audio, sr, ssml):
        # This is a simplified SSML-like processing
        if "<pitch>" in ssml:
            pitch = float(ssml.split("<pitch>")[1].split("</pitch>")[0])
            audio = self.pitch_shift(audio, sr, pitch)
        if "<rate>" in ssml:
            rate = float(ssml.split("<rate>")[1].split("</rate>")[0])
            audio = self.time_stretch(audio, sr, rate)
        return audio

    def voice_conversion(self, source_audio, target_audio, sr):
        # Simple voice conversion using MFCC manipulation
        source_mfcc = librosa.feature.mfcc(y=source_audio, sr=sr)
        target_mfcc = librosa.feature.mfcc(y=target_audio, sr=sr)

        converted_mfcc = source_mfcc + (target_mfcc - source_mfcc) * 0.5  # Adjust conversion strength
        return librosa.feature.inverse.mfcc_to_audio(converted_mfcc, sr=sr)

    def reduce_noise(self, audio, sr):
        # Simple noise reduction using spectral subtraction
        n_grad_freq = 2
        n_grad_time = 4
        n_fft = 2048
        win_length = 2048
        hop_length = 512
        n_std_thresh = 1.5
        prop_decrease = 1.0

        def _stft(y, n_fft, hop_length, win_length):
            return librosa.stft(y=y, n_fft=n_fft, hop_length=hop_length, win_length=win_length)

        # STFT of input audio
        stft = _stft(audio, n_fft, hop_length, win_length)
        stft_mag, stft_phase = librosa.magphase(stft)

        # Compute noise profile
        noise_stft_mag = np.min(stft_mag, axis=1, keepdims=True)

        # Perform noise reduction
        thresh = noise_stft_mag * n_std_thresh
        stft_mag_denoised = stft_mag - thresh
        stft_mag_denoised = np.maximum(stft_mag_denoised, 0)
        stft_denoised = stft_mag_denoised * np.exp(1.0j * stft_phase)

        # Inverse STFT
        audio_denoised = librosa.istft(stft_denoised, hop_length=hop_length, win_length=win_length)

        return audio_denoised

    def process_voice(self, input_file, output_file, modifications):
        audio, sr = self.load_audio(input_file)

        for mod in modifications:
            if mod['type'] == 'pitch_shift':
                audio = self.pitch_shift(audio, sr, mod['value'])
            elif mod['type'] == 'time_stretch':
                audio = self.time_stretch(audio, sr, mod['value'])
            elif mod['type'] == 'formant_shift':
                audio = self.formant_shift(audio, sr, mod['value'])
            elif mod['type'] == 'emotion':
                audio = self.apply_emotion(audio, sr, mod['value'])
            elif mod['type'] == 'ssml':
                audio = self.apply_ssml(audio, sr, mod['value'])
            elif mod['type'] == 'effect':
                self.audio_processor.add_effect(mod['value'])

        audio = self.audio_processor.process(audio, sr)
        audio = self.reduce_noise(audio, sr)

        self.save_audio(audio, sr, output_file)
        return audio, sr


# Example usage
if __name__ == "__main__":
    modifier = VoiceModifier()

    # Process voice 1
    modifications1 = [
        {'type': 'pitch_shift', 'value': 2},
        {'type': 'emotion', 'value': 'happy'},
        {'type': 'effect', 'value': ReverbEffect()},
    ]
    audio1, sr1 = modifier.process_voice("input1.wav", "output1.wav", modifications1)
    print("Voice 1 processed. Playing...")
    modifier.play_audio(audio1, sr1)

    # Process voice 2
    modifications2 = [
        {'type': 'formant_shift', 'value': 0.8},
        {'type': 'ssml', 'value': '<pitch>-2</pitch><rate>0.9</rate>'},
        {'type': 'effect', 'value': CompressionEffect()},
    ]
    audio2, sr2 = modifier.process_voice("input2.wav", "output2.wav", modifications2)
    print("Voice 2 processed. Playing...")
    modifier.play_audio(audio2, sr2)