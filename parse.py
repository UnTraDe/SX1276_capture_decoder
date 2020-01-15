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
FOLDER = "binding_rx_off"

FILE_MISO = "caps/" + FOLDER + "/MISO.csv"
FILE_MOSI = "caps/" + FOLDER + "/MOSI.csv"

# timeline indices

TIMESTAMP = 0
MISO = 1
MOSI = 2
FRAME_MARKER = 2 # not a typo

def insert_after(timeline, timestamp, value):
	for i, sample in enumerate(timeline):
		if timestamp > sample[TIMESTAMP]:
			continue
		else:
			timeline.insert(i, value)
			break

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

	with open(FILE_MISO) as f:
		next(f)
		for row in csv.reader(f, delimiter=','):
			timestamp = float(row[1])
			
			arr = []

			for b in row[2].split(" "):
				arr.append(int(b, 16))

			timeline.append([timestamp, arr])

	# merge MOSI into timeline

	i = 0

	with open(FILE_MOSI) as f:
		next(f)
		for row in csv.reader(f, delimiter=','):
			timestamp = float(row[1])
			
			if timeline[i][TIMESTAMP] != timestamp:
				raise Exception("timestamp mismatch, make sure all the input files are from the same capture!")
			
			arr = []

			for b in row[2].split(" "):
				arr.append(int(b, 16))

			timeline[i].append(arr)
			i = i + 1

	with open("timeline.txt", "w") as f:
		for s in timeline:
			f.write(f"{s[0]}, {s[1]}, {s[2]}\n")

	# read register map

	with open("reg_map.txt", "r") as f:
		lines = f.readlines()

	reg_map = {}

	for l in lines:
		elems = l.rstrip().split(' ')
		reg_map[int(elems[0], 16)] = elems[1]

	# generate user friendly text

	with open("output.txt", "w") as f:
		for frame in timeline:
			# first MOSI byte of the frame is the register address and it's MSB indicates read/write (1 = write, 0 = read)
			is_writing = (frame[MOSI][0] & 0x80)
			target_register = frame[MOSI][0] & 0x7F

			if target_register in reg_map:
				reg_name = reg_map[target_register]
			else:
				reg_name = ""
			
			read_or_write = "write" if is_writing else "read"
			payload = frame[MOSI][1:] if is_writing else frame[MISO][1:]

			f.write(f"{read_or_write} ({len(payload)} bytes) reg 0x{target_register:02x} ({reg_name}):\n")

			output = "\t"
			
			for b in payload:
				output += f"0x{b:02x} "
				
			f.write(output + "\n")

	# find frequency hopping map

	# frequency synthesizer step (Hz)
	fstep = 61

	first = True
	first_timestamp = 0

	for frame in timeline:
		is_writing = (frame[MOSI][0] & 0x80)
		target_register = frame[MOSI][0] & 0x7F

		if is_writing and target_register == 0x06:
			if first:
				first = False
				first_timestamp = frame[TIMESTAMP]

			t = frame[TIMESTAMP] - first_timestamp
			freq = (frame[MOSI][1] << 16 | frame[MOSI][2] << 8 | frame[MOSI][3]) * fstep

			#print(f"{t}: {freq}")
			print(f"{freq}")

	# extract channel data

	for frame in timeline:
		is_writing = (frame[MOSI][0] & 0x80)
		target_register = frame[MOSI][0] & 0x7F

		bs = []

		if is_writing and target_register == 0x00:

			for b in frame[MOSI][1:]:
				bs.append(b)

			chs = bs[8:]
			#print(chs)
			# ch = frame[9][MOSI] << 8 | frame[10][MOSI]

			ch1 = chs[0] << 3 | ((chs[1] >> 5) & 0b111)
			ch2 = (chs[1] & 0b11111) << 6 | ((chs[2] >> 2) & 0b111111)
			ch5 = (chs[5] & 0b1111) << 4 | ((chs[6] >> 1) & 0b1111111)
			
			string = ""

			for c in bs[4:]:
				string += format(c, "08b") + " "

			print(bs[3])

			#print(chs[0])
			#print(np.array([ch1, ch5]))

			#print(np.array(chs))
			#print(frame[9][MOSI])

			#pkt_timestamp = frame[1][MOSI] << 24 | frame[2][MOSI] << 16 | frame[3][MOSI] << 8 | frame[4][MOSI]
			#pkt_val = frame[5][MOSI] << 24 | frame[6][MOSI] << 16 | frame[7][MOSI] << 8 | frame[8][MOSI]

			#print(frame[4][MOSI])
			#print(bs[:3])


