import csv

# files

FILE_MISO = "caps/MISO.csv"
FILE_MOSI = "caps/MOSI.csv"
FILE_RAW = "caps/raw.csv"

# capture indices

FILE_RAW_CS_INDEX = 1

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
	timeline = []

	# create timeline from MISO file

	with open(FILE_MISO) as f:
		for row in csv.reader(f, delimiter=','):
			timestamp = float(row[1])
			timeline.append([timestamp, int(row[2], 16)])

	# merge MOSI into timeline

	i = 0

	with open(FILE_MOSI) as f:
		for row in csv.reader(f, delimiter=','):
			timestamp = float(row[1])
			
			if timeline[i][TIMESTAMP] != timestamp:
				raise Exception("timestamp mismatch, make sure all the input files are from the same capture!")
			
			timeline[i].append(int(row[2], 16))
			i = i + 1

	# add frame start / frame end markers (determined by CS line)

	prev = 1

	with open(FILE_RAW) as f:
		i = 0
		first_idle_found = False

		for row in csv.reader(f, delimiter=','):
			# skip first 5 rows
			if i < 5:
				i = i + 1
				continue

			timestamp = float(row[0])
			value = int(row[FILE_RAW_CS_INDEX])

			# if CS is low before first_idle_found we are in the middle of the frame,
			# so skip ahead until this partial frame is ended
			if not first_idle_found:
				if value == 1:
					first_idle_found = True
					print(f"first idle CS sample found at {timestamp}")
				else:
					continue

			if value == 0 and prev == 1: # high > low transition
				insert_after(timeline, timestamp, [timestamp, 0, "frame_start"])
			elif value == 1 and prev == 0: # low > high transition
				insert_after(timeline, timestamp, [timestamp, 0, "frame_end"])

			prev = value

	with open("timeline.txt", "w") as f:
		for s in timeline:
			f.write(str(s) + "\n")

	# seperate the timeline into data frames

	data = []
	frame = []
	in_frame = False

	for sample in timeline:
		if in_frame:
			if type(sample[FRAME_MARKER]) == str and sample[FRAME_MARKER] == "frame_end":
				data.append(frame.copy())
				frame.clear()
				in_frame = False
			elif type(sample[FRAME_MARKER]) == str and sample[FRAME_MARKER] == "frame_start":
				raise Exception("frame_start while in frame")
			else:
				frame.append(sample)
		else:
			if type(sample[FRAME_MARKER]) == str and sample[FRAME_MARKER] == "frame_start":
				in_frame = True
			else:
				raise Exception("invalid row while outside of frame")

	# uncomment this if you want to see the last frame even if it's truncated
	# if in_frame: # ended mid frame
	# 	data.append(frame.copy())

	# read register map

	with open("reg_map.txt", "r") as f:
		lines = f.readlines()

	reg_map = {}

	for l in lines:
		elems = l.rstrip().split(' ')
		reg_map[int(elems[0], 16)] = elems[1]

	# generate user friendly text

	for frame in data:
		# first MOSI byte of the frame is the register address and it's MSB indicates read/write (1 = write, 0 = read)
		is_writing = (frame[0][MOSI] & 0x80)
		target_register = frame[0][MOSI] & 0x7F

		if target_register in reg_map:
			reg_name = reg_map[target_register]
		else:
			reg_name = ""
		
		read_or_write = "write" if is_writing else "read"

		print(f"{read_or_write} ({len(frame) - 1} bytes) reg 0x{target_register:02x} ({reg_name}):")

		payload = "\t"

		for t in frame[1:]:
			payload += "0x{:02x} ".format(t[MOSI] if is_writing else t[MISO])

		print(payload)