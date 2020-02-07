import csv
import sys
import numpy as np

# files

#FOLDER = "running_moving_ch1"
#FOLDER = "running_idle"
#FOLDER = "running_ch5_switch_low"
#FOLDER = "running_ch5_switch_high"
#FOLDER = "running_th_-13"
#FOLDER = "running_th_29"
FOLDER = "idle_868"

FILE_MISO = "caps/" + FOLDER + "/MISO.csv"
FILE_MOSI = "caps/" + FOLDER + "/MOSI.csv"

# timeline indices

TIMESTAMP = 0
MISO = 1
MOSI = 2
FRAME_MARKER = 2 # not a typo


FrSkyX_CRC_Short = [0x0000, 0x1189, 0x2312, 0x329B, 0x4624, 0x57AD, 0x6536, 0x74BF, 0x8C48, 0x9DC1, 0xAF5A, 0xBED3, 0xCA6C, 0xDBE5, 0xE97E, 0xF8F7 ]

def FrSkyX_CRCTable(val):
	word = FrSkyX_CRC_Short[val&0x0F]
	val =  val // 16

	return word ^ (0x1081 * val)

def FrSkyX_crc(data):
	crc = 0

	for b in data:
		crc = ((crc<<8) & 0xffff) ^ FrSkyX_CRCTable( (crc>>8) ^ b)

	return crc

def find_freq_list(timeline):
	freq_list = []
	fstep = 61 # frequency synthesizer step (Hz)
	i = 0
	ch_step_size = None

	for frame in timeline:
		is_writing = frame[MOSI][0] & 0x80
		target_register = frame[MOSI][0] & 0x7F

		if is_writing and target_register == 0x06:
			freq = (frame[MOSI][1] << 16 | frame[MOSI][2] << 8 | frame[MOSI][3]) * fstep
			freq_list.append([freq])
		elif is_writing and target_register == 0x00:
			freq_list[i].append(frame[MOSI][4]) # current channel index
			i = i + 1

			if ch_step_size == None:
				ch_step_size = frame[MOSI][5]
			elif ch_step_size != frame[MOSI][5]:
				raise Exception("found different step size")
				
	freq_map, instance_count = np.unique(np.array(freq_list), axis=0, return_counts=True)
	freq_map = freq_map[freq_map[:, 1].argsort()]

	return (freq_list, ch_step_size, freq_map, instance_count)

def decode_frame_channels(raw_ch):
	chs = [i for i in range(8)]
	chs[0] = ((raw_ch[10] << 8) & 0xF00) | raw_ch[9]
	chs[1] = ((raw_ch[11] << 4) & 0xFF0) | (raw_ch[10] >> 4)
	chs[2] = ((raw_ch[13] << 8) & 0xF00) | raw_ch[12]
	chs[3] = ((raw_ch[14] << 4) & 0xFF0) | (raw_ch[13] >> 4)
	chs[4] = ((raw_ch[16] << 8) & 0xF00) | raw_ch[15]
	chs[5] = ((raw_ch[17] << 4) & 0xFF0) | (raw_ch[16] >> 4)
	chs[6] = ((raw_ch[19] << 8) & 0xF00) | raw_ch[18]
	chs[7] = ((raw_ch[20] << 4) & 0xFF0) | (raw_ch[19] >> 4)

	rc = [-1 for i in range(16)]

	# every channel is 11 bit + 1 ""is shifted" bit
	# first bit in the channel indicates whether it's part of the upper channels (9-16) or lower (1-8) (0 - lower 1 - upper)

	for i, c in enumerate(chs):
		shifted = c & 0x800 # first bit indicates if this channels is in the lower or upper channel range (0 - lower 1 - upper)
		val = c & 0x7FF # rest of the 11 bits are the actual channel value
		rc[i + 8 if shifted else i] = ((val - 64) * 2 + 860 * 3) // 3 # not sure what's going on here

	return rc

def extract_channel_data(timeline):
	rc_data = []

	for frame in timeline:
		is_writing = (frame[MOSI][0] & 0x80)
		target_register = frame[MOSI][0] & 0x7F

		if is_writing and target_register == 0x00:
			raw_ch = frame[MOSI]
			rc = decode_frame_channels(raw_ch)
			rc_data.append(rc)
	
	return rc_data



if __name__ == "__main__":

	if len(sys.argv) == 3:
		FILE_MISO = sys.argv[1]
		FILE_MOSI = sys.argv[2]
	elif len(sys.argv) == 2:
		FOLDER = sys.argv[1]
		FILE_MISO = FOLDER + "/MISO.csv"
		FILE_MOSI = FOLDER + "/MOSI.csv"

	timeline = []

	# create timeline from MISO file

	# with open(FILE_MISO) as f:
	# 	next(f)
	# 	for row in csv.reader(f, delimiter=','):
	# 		timestamp = float(row[1])
			
	# 		arr = []

	# 		for i, b in enumerate(row[2].split(" ")):
	# 			try:
	# 				arr.append(int(b, 16))
	# 			except ValueError:
	# 				raise Exception(f"none int literal: {b} at line: {i}")

	# 		timeline.append([timestamp, arr])

	# merge MOSI into timeline

	# i = 0

	# with open(FILE_MOSI) as f:
	# 	next(f)
	# 	for row in csv.reader(f, delimiter=','):
	# 		timestamp = float(row[1])
			
	# 		if timeline[i][TIMESTAMP] != timestamp:
	# 			raise Exception("timestamp mismatch, make sure all the input files are from the same capture!")
			
	# 		arr = []

	# 		for b in row[2].split(" "):
	# 			arr.append(int(b, 16))

	# 		timeline[i].append(arr)
	# 		i = i + 1

	with open(FILE_MOSI) as f:
		next(f)
		for row in csv.reader(f, delimiter=','):
			timestamp = float(row[1])
			
			arr = []

			for i, b in enumerate(row[2].split(" ")):
				try:
					arr.append(int(b, 16))
					ok = True
				except ValueError:
					raise Exception(f"none int literal: {b} at line: {i}")

			timeline.append([timestamp, [i for i in range(len(arr))], arr])

			

	with open("timeline.txt", "w") as f:
		for s in timeline:
			f.write(f"{s[0]}, {s[1]}, {s[2]}\n")

	# read register map(s)

	with open("reg_map_fsk_ook.txt", "r") as f:
		lines = f.readlines()

	reg_map_fsk_ook = {}

	for l in lines:
		elems = l.rstrip().split(' ')
		reg_map_fsk_ook[int(elems[0], 16)] = elems[1]

	with open("reg_map_lora.txt", "r") as f:
		lines = f.readlines()

	reg_map_lora = {}

	for l in lines:
		elems = l.rstrip().split(' ')
		reg_map_lora[int(elems[0], 16)] = elems[1]

	# generate user friendly text

	chip_mode_lora = None

	with open("output.txt", "w") as f:
		for frame in timeline:
			# first MOSI byte of the frame is the register address and it's MSB indicates read/write (1 = write, 0 = read)
			is_writing = (frame[MOSI][0] & 0x80)
			target_register = frame[MOSI][0] & 0x7F

			if is_writing and target_register == 0x01: # OpMode register
				if frame[MOSI][1] & 0x80: # mode bit
					chip_mode_lora = True
				else:
					chip_mode_lora = False

			if chip_mode_lora is None:
				continue
				
			reg_map = reg_map_lora if chip_mode_lora else reg_map_fsk_ook

			if target_register in reg_map:
				reg_name = reg_map[target_register]
			else:
				reg_name = ""
			
			read_or_write = "write" if is_writing else "read"
			payload = frame[MOSI][1:] if is_writing else frame[MISO][1:]

			f.write(f"{read_or_write} ({len(payload)} bytes) reg 0x{target_register:02x} ({reg_name}): (mode: {('LoRa' if chip_mode_lora else 'FSK/OOK')})\n")

			output = "\t"
			
			for b in payload:
				output += f"0x{b:02x} "
				
			f.write(output + "\n")

	# find frequency hopping map
	
	# freq_list, step_size, freq_map, instance_count = find_freq_list(timeline)

	# for i, e in enumerate(freq_map):
	# 	print(f"{e[1]}: {e[0]}") # 	print(f"{e[1]}: {e[0]}  {instance_count[i]}")

	# print(f"len: {len(freq_map)}, step size: {step_size}")


	# extract channel data

	# rc_data = extract_channel_data(timeline)

	# for rc in rc_data:
	# 	print(rc)

	# # find failsafe data

	# for frame in timeline:
	# 	is_writing = (frame[MOSI][0] & 0x80)
	# 	target_register = frame[MOSI][0] & 0x7F

	# 	if is_writing and target_register == 0x00 and frame[MOSI][8] != 0x00:
	# 		rc = decode_frame_channels(frame[MOSI])
	# 		print(rc)

	# for frame in timeline:
	# 	is_writing = (frame[MOSI][0] & 0x80)
	# 	target_register = frame[MOSI][0] & 0x7F

	# 	if is_writing and target_register == 0x00:
	# 		for i in frame[MOSI][1:]:
	# 			print(f"{i:02X} ", end="")

	# 		print("")


	