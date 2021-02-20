#define u8  uint8_t
#define u16 uint16_t
#define u32 uint32_t

#define ES16(_val) \
	((u16)(((((u16)_val) & 0xff00) >> 8) | \
	       ((((u16)_val) & 0x00ff) << 8)))

#define ES32(_val) \
	((u32)(((((u32)_val) & 0xff000000) >> 24) | \
	       ((((u32)_val) & 0x00ff0000) >> 8 ) | \
	       ((((u32)_val) & 0x0000ff00) << 8 ) | \
	       ((((u32)_val) & 0x000000ff) << 24)))
	       

// imagefont.bin header structure definition
typedef struct {
	uint16_t bitordertype;
	uint16_t nbrEntries;
	uint32_t indexStart;
} imagefontHeader_t;

// index entries structure definition
typedef struct {
	uint32_t paletteStart;
	uint16_t paletteCompSize;
	uint16_t paletteDecompSize;
	uint16_t unicodeId;
	uint16_t imageWidth;
	uint16_t imageHeight;
	uint16_t unknownData1;
} indexEntry_t;

// palette header structure definition
typedef struct {
	uint16_t colorsCount;
	uint8_t colorChannel;
	uint8_t framesCount;
	uint16_t animTime;
} paletteHeader_t;

// frame structure definition
typedef struct {
	uint32_t frameDataOffset;
	uint16_t frameDataLength;
	uint16_t frameTime;
	uint8_t unknownData2;
	uint8_t alphaMask;
	uint16_t unknownData3;
} frameInfo_t;
