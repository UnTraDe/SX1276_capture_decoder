#include <SPI.h>

static HardwareSerial _serial(PA10, PA9);
//static SPIClass _spi(PB5, PB4, PB3, PA15);
static SPIClass _spi(PB5, PB4, PB3);
static SPISettings _spi_settings(8e6, MSBFIRST, SPI_MODE0);


#define REG_IRQ_FLAGS_MASK			0x11

#define REG_PAYLOAD_LENGTH			0x22


#define REG_FIFO_ADDR_PTR			0x0D
#define REG_FIFO_TX_BASE_ADDR		0x0E

#define REG_OP_MODE 				0x01
#define REG_DETECT_OPTIMIZE 		0x31
#define REG_DIO_MAPPING1			0x40
#define REG_VERSION 				0x42


#define REG_MODEM_CONFIG1			0x1D
#define REG_MODEM_CONFIG2			0x1E
#define REG_MODEM_CONFIG3			0x26

#define REG_PREAMBLE_LSB			0x21
#define REG_DETECTION_THRESHOLD		0x37

#define REG_LNA						0x0C

#define REG_HOP_PERIOD				0x24

#define REG_PA_DAC					0x4D

#define REG_PA_CONFIG				0x09

#define REG_FRF_MSB					0x06

#define REG_FIFO					0x00

#define REG_OCP						0x0B

uint32_t freq_map[] =
{
	914472960, 	// 0
	914972672,	// 1
	915472384,  // 2
	915972096,  // 3
	916471808,  // 4
	916971520,  // 5
	917471232,  // 6
	917970944,  // 7
	918470656,  // 9
	918970368,  // 10
	919470080,
	919969792,
	920469504,
	920969216,
	921468928,
	921968640,
	922468352,
	922968064,
	923467776,
	923967488,
	924467200,
	924966912,
	925466624,
	925966336,
	926466048,
	926965760,
	927465472,

	// last two determined by step?
	0,
	0
};


uint8_t weird[2][16] =
{
{0x00, 0x04, 0x40, 0x00, 0x04, 0x40, 0x00, 0x04, 0x40, 0x00, 0x04, 0x40, 0x08, 0x00, 0x00, 0x00},
{0x00, 0x0C, 0xC0, 0x00, 0x0C, 0xC0, 0x00, 0x0C, 0xC0, 0x00, 0x0C, 0xC0, 0x08, 0x00, 0x00, 0x00}
};


uint8_t _step = 20;

void setup()
{   
	pinMode(PC13, OUTPUT);
	_serial.begin(115200);
	_serial.println("startup");

	pinMode(PB7, OUTPUT);
	digitalWrite(PB7, LOW);
	delay(1); // actually requires only 100us
	digitalWrite(PB7, HIGH);
	delay(5); // wait 5ms before usign the chip

	pinMode(PA15, OUTPUT);
	digitalWrite(PA15, HIGH);
	_spi.begin();

	// verify connection and chip version
	uint8_t version = readRegister(REG_VERSION);

	if(version == 0x12)
	{
		_serial.println("connection verified");
	}
	else
	{
		_serial.print("got version: ");
		_serial.print(version, HEX);
		_serial.println(" but expected 0x12, most likely the device is not connnected properly");
	}

	freq_map[27] = freq_map[_step];
	freq_map[28] = freq_map[_step+1];

	writeRegister(REG_OP_MODE, 0x80); // sleep
	writeRegister(REG_OP_MODE, 0x81); // standby

	uint8_t buffer[2];
	buffer[0] = 0x00;
	buffer[1] = 0x00;
	writeRegisters(REG_DIO_MAPPING1, buffer, 2);

	uint8_t val = readRegister(REG_DETECT_OPTIMIZE);
	val = (val & 0b11111000) | 0b00000101;
	writeRegister(REG_DETECT_OPTIMIZE, val);

	// val = readRegister(REG_MODEM_CONFIG2);
	// val = (val & 0b00011111) | 0b11000000;
	// writeRegister(REG_MODEM_CONFIG2, val);

	writeRegister(REG_MODEM_CONFIG1, 0x93);

	
	writeRegister(REG_MODEM_CONFIG2, 0x60);

	val = readRegister(REG_MODEM_CONFIG3);
	val = (val & 0b11110011);
	writeRegister(REG_MODEM_CONFIG3, val);

	writeRegister(REG_PREAMBLE_LSB, 9);

	writeRegister(REG_DETECTION_THRESHOLD, 0x0C);

	writeRegister(REG_LNA, 0x23);

	writeRegister(REG_HOP_PERIOD, 0x00);

	val = readRegister(REG_PA_DAC);
	val = (val & 0b11111000) | 0b00000111;
	writeRegister(REG_PA_DAC, val);



	//writeRegister(REG_OCP, 0x20 | (0x1F & 17));
	//writeRegister(REG_PA_CONFIG, 0x8F);


	// temp?
	//writeRegister(REG_PA_CONFIG, 0xF0);

}

void loop()
{
	// digitalWrite(PC13, HIGH);
	// delay(500);
	// digitalWrite(PC13, LOW);
	// delay(500);

	// uint8_t val = readRegister(0x42);

	// _serial.print("val:" );
	// _serial.println(val);

	//digitalWrite(PC13, HIGH);

	static uint16_t rc = 1000;

	
	rc += 20;

	transmit(rc);
	delay(18);


	if(rc >= 2000)
		rc = 1000;

	//digitalWrite(PC13, LOW);
}

void transmit(uint16_t rc)
{
	static uint16_t index = 0;
	uint8_t buffer[3];

	writeRegister(REG_OP_MODE, 0x81); // STDBY
	writeRegister(REG_IRQ_FLAGS_MASK, 0xbf);


	buffer[0] = 0x00;
	buffer[1] = 0x00;
	writeRegisters(REG_DIO_MAPPING1, buffer, 2);

	// writeRegister(REG_PAYLOAD_LENGTH, 13);

	// writeRegister(REG_FIFO_ADDR_PTR, 0x00);

	// writeRegister(REG_OP_MODE, 0x85); // RXCONTINUOUS
	// delay(10); // 10 ms

	// writeRegister(REG_OP_MODE, 0x81); // STDBY

	writeRegister(REG_PA_CONFIG, 0xF0);

	uint32_t freq = freq_map[index] / 61;
	
	buffer[0] = (freq & (0xFF << 16)) >> 16;
	buffer[1] = (freq & (0xFF << 8)) >> 8;
	buffer[2] = freq & 0xFF;
	
	writeRegisters(REG_FRF_MSB, buffer, 3); // set next freq
	
	delayMicroseconds(500);

	writeRegister(REG_PAYLOAD_LENGTH, 26);
	writeRegister(REG_FIFO_TX_BASE_ADDR, 0x00);
	writeRegister(REG_FIFO_ADDR_PTR, 0x00);

	

	uint8_t payload[26] = { 0 }; 

	//header?
	payload[0] = 0x3C; // ????
	payload[1] = 0x04; // ????
	payload[2] = 0x3B; // ????

	// next channel index
	payload[3] = index;

	// step size and last 2 channels start index?
	payload[4] = _step;

	// radio number
	payload[5] = 0x1E;

	// binding mode?
	payload[6] = 0x00; // 0x00 regular / 0x41 bind?

	// ????
	payload[7] = 0x00;

	//memcpy(&payload[8], &weird[index % 2][0], 16);

	uint16_t val = (uint16_t)(rc * 1.5f) - 1226;

	// ch1 data
	payload[8] = val;
	payload[9] = (val >> 8) & 0b0111;

	uint16_t crc = frskysx_crc(payload, 24);

	payload[24] = crc; // low byte
	payload[25] = crc >> 8; // high byte


	// write payload to fifo
	writeRegisters(REG_FIFO, payload, 26);

	index = (index + _step) % 29;

	//delayMicroseconds(10); // 10us
	writeRegister(REG_OP_MODE, 0x83); // TX

	// need to clear RegIrqFlags?
}

uint8_t readRegister(uint8_t address)
{
	digitalWrite(PA15, LOW);

	_spi.beginTransaction(_spi_settings);
	_spi.transfer(address & 0b01111111); // MSB 0 = read
	uint8_t value = _spi.transfer(0x00);
	_spi.endTransaction();

	digitalWrite(PA15, HIGH);

	return value;
}

uint8_t readRegisters(uint8_t address)
{
	digitalWrite(PA15, LOW);

	_spi.beginTransaction(_spi_settings);
	_spi.transfer(address & 0b01111111); // MSB 0 = read
	uint8_t value = _spi.transfer(0x00);
	_spi.endTransaction();

	digitalWrite(PA15, HIGH);

	return value;
}

uint8_t writeRegister(uint8_t address, uint8_t value)
{
	digitalWrite(PA15, LOW);

	_spi.beginTransaction(_spi_settings);
	_spi.transfer(address | 0x80); // MSB 1 = write
	uint8_t prev_value = _spi.transfer(value);
	_spi.endTransaction();

	digitalWrite(PA15, HIGH);

	return prev_value;
}

uint8_t writeRegisters(uint8_t address, uint8_t* buffer, uint8_t length)
{
	digitalWrite(PA15, LOW);

	_spi.beginTransaction(_spi_settings);
	_spi.transfer(address | 0x80); // MSB 1 = write
	_spi.transfer(buffer, length);
	_spi.endTransaction();

	digitalWrite(PA15, HIGH);

	return 0;
}

const uint16_t frskyx_crc_short[] =
{
	0x0000, 0x1189, 0x2312, 0x329B, 0x4624, 0x57AD, 0x6536, 0x74BF,
	0x8C48, 0x9DC1, 0xAF5A, 0xBED3, 0xCA6C, 0xDBE5, 0xE97E, 0xF8F7
};

static uint16_t frskysx_crc_table(uint8_t val)
{
	uint16_t word;
	word = frskyx_crc_short[val & 0x0F];
	val /= 16;
	return word ^ (0x1081 * val);
}

uint16_t frskysx_crc(uint8_t* data, uint8_t len)
{
	uint16_t crc = 0;
	for (uint8_t i = 0; i < len; i++)
		crc = (crc << 8) ^ frskysx_crc_table((uint8_t)(crc >> 8) ^ *data++);
	return crc;
}

void dump_registers()
{

}