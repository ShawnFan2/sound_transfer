import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import scrolledtext, messagebox
from scipy.signal import find_peaks
import logging
import threading

SAMPLE_RATE = 44100  # 采样率
BIT_DURATION = 0.1    # 每个比特的持续时间（秒）
FREQ_0 = 1000         # 表示比特0的频率（Hz）
FREQ_1 = 2000         # 表示比特1的频率（Hz）
PREAMBLE = '10101010' # 前导码，用于同步

logging.basicConfig(
    filename='receiver.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'  # 每次运行时覆盖日志文件,
)
logger = logging.getLogger()

def audio_to_bits(audio_signal):
    """将音频信号转换为比特串（FSK解调）"""
    try:
        samples_per_bit = int(SAMPLE_RATE * BIT_DURATION)
        num_bits = len(audio_signal) // samples_per_bit
        bits = ''
        logger.debug(f"音频信号样本总数: {len(audio_signal)}，每比特样本数: {samples_per_bit}")
        for i in range(num_bits):
            bit_signal = audio_signal[i * samples_per_bit : (i + 1) * samples_per_bit]
            # 使用FFT分析频率
            fft = np.fft.fft(bit_signal)
            freqs = np.fft.fftfreq(len(fft), 1/SAMPLE_RATE)
            magnitudes = np.abs(fft)
            peak_freq = freqs[np.argmax(magnitudes[:len(magnitudes)//2])]
            # 判定为'1'还是'0'
            bit = '1' if abs(peak_freq - FREQ_1) < abs(peak_freq - FREQ_0) else '0'
            bits += bit
            logger.debug(f"第 {i+1} 比特的峰值频率: {peak_freq} Hz，解调为: {bit}")
        logger.debug(f"解调得到的比特串: {bits}")
        return bits
    except Exception as e:
        logger.error(f"音频信号转换为比特串时出错: {e}")
        raise

def find_preamble(bits):
    """查找前导码的位置，确保前导码连续出现多次"""
    try:
        preamble_sequence = PREAMBLE * 3  # 前导码重复3次
        for i in range(len(bits) - len(preamble_sequence) + 1):
            if bits[i:i+len(preamble_sequence)] == preamble_sequence:
                logger.debug(f"前导码 '{preamble_sequence}' 在位置 {i} 被检测到。")
                return i + len(preamble_sequence)
        logger.debug(f"前导码 '{preamble_sequence}' 未被检测到。")
        return None
    except Exception as e:
        logger.error(f"查找前导码时出错: {e}")
        raise

def bits_to_text(bits):
    """将二进制比特串转换为文本"""
    try:
        chars = []
        for b in range(0, len(bits), 8):
            byte = bits[b:b+8]
            if len(byte) < 8:
                break
            chars.append(chr(int(byte, 2)))
        text = ''.join(chars)
        logger.debug(f"比特串转换为文本: {text}")
        return text
    except Exception as e:
        logger.error(f"比特串转换为文本时出错: {e}")
        raise

class ReceiverApp:
    def __init__(self, master):
        self.master = master
        master.title("声波接收端")
        master.geometry("500x500")
        
        # 录音时间设置
        self.duration_label = tk.Label(master, text="录音时长（秒）：")
        self.duration_label.pack(pady=5)
        
        self.duration_entry = tk.Entry(master)
        self.duration_entry.insert(0, "15")  # 默认15秒
        self.duration_entry.pack(pady=5)
        
        # 开始录音按钮
        self.record_button = tk.Button(master, text="开始录音", command=self.start_recording)
        self.record_button.pack(pady=10)
        
        # 状态显示
        self.status_label = tk.Label(master, text="", fg="blue")
        self.status_label.pack(pady=5)
        
        # 接收文本显示框
        self.received_text = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=60, height=15)
        self.received_text.pack(pady=10)
    
    def start_recording(self):
        try:
            duration = float(self.duration_entry.get())
            if duration <= 0:
                raise ValueError("录音时长必须大于0。")
            logger.info(f"用户设置的录音时长: {duration} 秒")
        except ValueError as e:
            messagebox.showerror("输入错误", f"无效的录音时长：{e}")
            logger.error(f"录音时长输入无效: {e}")
            return
        
        self.status_label.config(text="正在录音...")
        self.received_text.delete("1.0", tk.END)
        logger.info("开始录音。")
        self.master.update()
        
        threading.Thread(target=self.record_and_process, args=(duration,)).start()
    
    def record_and_process(self, duration):
        try:
            audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float64')
            sd.wait()
            audio = audio.flatten()
            logger.info("录音完成。")
            self.status_label.config(text="录音完成，正在解码...")
            self.master.update()
            
            bits = audio_to_bits(audio)
            start = find_preamble(bits)
            if start is None:
                self.status_label.config(text="未检测到前导码。")
                messagebox.showwarning("解码失败", "未检测到前导码。")
                logger.warning("未检测到前导码。")
                return
            
            # 解析包头（16位，表示数据长度）
            header_bits = bits[start:start+16]
            data_length = int(header_bits, 2)
            logger.debug(f"包头解析得到的数据长度: {data_length} 位")
            
            # 检查是否有足够的比特进行解析
            if len(bits) < start + 16 + data_length:
                logger.warning("接收到的比特数不足以解析完整的有效载荷。")
                self.status_label.config(text="接收到的比特数不足以解析完整的有效载荷。")
                messagebox.showwarning("解码失败", "接收到的比特数不足以解析完整的有效载荷。")
                return
            
            # 解析有效载荷
            payload_bits = bits[start+16 : start+16+data_length]
            message = bits_to_text(payload_bits)
            
            self.received_text.insert(tk.END, message)
            self.status_label.config(text="解码完成。")
            logger.info(f"成功解码接收到的消息: {message}")
        except Exception as e:
            self.status_label.config(text="解码失败。")
            messagebox.showerror("解码错误", f"解码过程中发生错误：{e}")
            logger.error(f"解码过程中发生错误: {e}")

def main():
    logger.info("接收端程序启动。")
    root = tk.Tk()
    app = ReceiverApp(root)
    root.mainloop()
    logger.info("接收端程序关闭。")

if __name__ == "__main__":
    main()