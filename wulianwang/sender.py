import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import scrolledtext, messagebox
import logging
import sys

SAMPLE_RATE = 44100  # 采样率
BIT_DURATION = 0.1    # 每个比特的持续时间（秒）
FREQ_0 = 1000         # 表示比特0的频率（Hz）
FREQ_1 = 2000         # 表示比特1的频率（Hz）
PREAMBLE = '10101010' # 前导码，用于同步

logging.basicConfig(
    filename='sender.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'  
)
logger = logging.getLogger()

def text_to_bits(text):
    """将文本转换为二进制比特串"""
    try:
        bits = ''.join([format(ord(c), '08b') for c in text])
        logger.debug(f"文本转换为比特串: {bits}")
        return bits
    except Exception as e:
        logger.error(f"文本转换为比特串时出错: {e}")
        raise

def bits_to_audio(bits):
    """将比特串转换为音频信号（FSK调制）"""
    try:
        audio = np.array([])
        for bit in bits:
            freq = FREQ_1 if bit == '1' else FREQ_0
            t = np.linspace(0, BIT_DURATION, int(SAMPLE_RATE * BIT_DURATION), endpoint=False)
            wave = 1.0 * np.sin(2 * np.pi * freq * t)  # 增加幅度到1.0
            audio = np.concatenate((audio, wave))
        logger.debug("比特串成功转换为音频信号。")
        return audio
    except Exception as e:
        logger.error(f"比特串转换为音频信号时出错: {e}")
        raise

def build_packet(data_bits):
    """构建数据包，包含前导码、包头和有效载荷"""
    try:
        preamble_bits = PREAMBLE * 3  # 重复前导码3次
        header_bits = f"{len(data_bits):016b}"  # 16位包头表示数据长度
        packet_bits = preamble_bits + header_bits + data_bits
        logger.debug(f"数据包构建完成: {packet_bits}")
        return packet_bits
    except Exception as e:
        logger.error(f"构建数据包时出错: {e}")
        raise

class SenderApp:
    def __init__(self, master):
        self.master = master
        master.title("声波发送端")
        master.geometry("600x500")
        
        # 输入标签
        self.label = tk.Label(master, text="输入要发送的文本：")
        self.label.pack(pady=10)
        
        # 文本输入框
        self.text_input = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=70, height=15)
        self.text_input.pack(pady=10)
        
        # 发送按钮
        self.send_button = tk.Button(master, text="发送", command=self.send_text, width=20, height=2)
        self.send_button.pack(pady=10)
        
        # 状态显示
        self.status_label = tk.Label(master, text="", fg="green")
        self.status_label.pack(pady=10)
    
    def send_text(self):
        message = self.text_input.get("1.0", tk.END).strip()
        logger.info(f"用户输入的消息: {message}")
        if not message:
            messagebox.showwarning("输入错误", "请输入要发送的文本。")
            logger.warning("发送操作取消：用户未输入任何文本。")
            return
        try:
            data_bits = text_to_bits(message)
            packet_bits = build_packet(data_bits)
            audio_signal = bits_to_audio(packet_bits)
            self.status_label.config(text="正在播放音频信号...")
            logger.info("开始播放音频信号。")
            self.master.update()
            sd.play(audio_signal, SAMPLE_RATE)
            sd.wait()
            self.status_label.config(text="发送完成。")
            logger.info("音频信号播放完成。")
        except Exception as e:
            messagebox.showerror("发送错误", f"发送过程中发生错误：{e}")
            self.status_label.config(text="发送失败。")
            logger.error(f"发送过程中发生错误: {e}")

def main():
    logger.info("发送端程序启动。")
    root = tk.Tk()
    app = SenderApp(root)
    root.mainloop()
    logger.info("发送端程序关闭。")

if __name__ == "__main__":
    main()