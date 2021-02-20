/*
*
*	ImageFont.bin Extractor - (c) 2021 by Bucanero - www.bucanero.com.ar
*
* This tool is based on the original imgftt.py tool by littlebalup
*	https://www.psx-place.com/threads/imagefont-bin-tool-for-ps3-and-vita.25150/
*
*/

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "unicode.h"
#include "miniz.h"
#include "svpng.h"
#include "imgfont.h"


int read_buffer(const char *file_path, u8 **buf, size_t *size)
{
	FILE *fp;
	u8 *file_buf;
	size_t file_size;
	
	if ((fp = fopen(file_path, "rb")) == NULL)
        return -1;
	fseek(fp, 0, SEEK_END);
	file_size = ftell(fp);
	fseek(fp, 0, SEEK_SET);
	file_buf = (u8 *)malloc(file_size);
	fread(file_buf, 1, file_size, fp);
	fclose(fp);
	
	if (buf)
        *buf = file_buf;
	else
        free(file_buf);
	if (size)
        *size = file_size;
	
	return 0;
}

int write_buffer(const char *file_path, u8 *buf, size_t size)
{
	FILE *fp;
	
	if ((fp = fopen(file_path, "wb")) == NULL)
        return -1;
	fwrite(buf, 1, size, fp);
	fclose(fp);
	
	return 0;
}

void bswap_imagefontHeader(imagefontHeader_t* img_hdr)
{
	img_hdr->nbrEntries = ES16(img_hdr->nbrEntries);
	img_hdr->indexStart = ES32(img_hdr->indexStart);
}

void bswap_indexEntry(indexEntry_t* index)
{
	index->paletteStart = ES32(index->paletteStart);
	index->paletteCompSize = ES16(index->paletteCompSize);
	index->paletteDecompSize = ES16(index->paletteDecompSize);
	index->unicodeId = ES16(index->unicodeId);
	index->imageWidth = ES16(index->imageWidth);
	index->imageHeight = ES16(index->imageHeight);
}

void bswap_paletteHeader(paletteHeader_t* palette)
{
	palette->colorsCount = ES16(palette->colorsCount);
	palette->animTime = ES16(palette->animTime);
}

void bswap_frameInfo(frameInfo_t* frame)
{
	frame->frameDataOffset = ES32(frame->frameDataOffset); 
	frame->frameDataLength = ES16(frame->frameDataLength);
	frame->frameTime = ES16(frame->frameTime);
}

void exportEntry(indexEntry_t* entry, const u8* imagefontRawData, int bswap)
{
	size_t len;
	char outfile[128];

	ucs2_to_utf8(entry->unicodeId, (u8*) outfile);

	printf("IMAGE_INFO; Info from index entry:\n");
	printf("IMAGE_INFO;    unicode code point : U+%04X\n", entry->unicodeId);
	printf("IMAGE_INFO;    UTF-8 hex value (calculated) : %02X %02X %02X\n", (u8) outfile[0], (u8) outfile[1], (u8) outfile[2]);
	printf("IMAGE_INFO;    image size : %d x %d\n", entry->imageWidth, entry->imageHeight);
	printf("IMAGE_INFO;    palette size : %d\n", entry->paletteDecompSize);
	printf("IMAGE_INFO;    unknown_data_1 0x%04X\n", entry->unknownData1);

	u8* paletteRawData = malloc(entry->paletteDecompSize);
	
	if (tinfl_decompress_mem_to_mem(paletteRawData, entry->paletteDecompSize, imagefontRawData + entry->paletteStart, entry->paletteCompSize, TINFL_FLAG_PARSE_ZLIB_HEADER) != entry->paletteDecompSize)
	{
		printf("Palette Decompress ERROR!\n");
		exit(1);
	}

	paletteHeader_t* palette = (paletteHeader_t*) paletteRawData;		
	if (bswap) bswap_paletteHeader(palette);

	printf("IMAGE_INFO; Info from palette header:\n");
	printf("IMAGE_INFO;    color count : %d\n", palette->colorsCount);
	printf("IMAGE_INFO;    color channel : %d bytes (%d bits)\n", palette->colorChannel, palette->colorChannel*8);
	printf("IMAGE_INFO;    frame count : %d\n", palette->framesCount);
	printf("IMAGE_INFO;    total animation time : %.3f second(s)\n", (float)(palette->animTime / 100));
	if (palette->animTime > 0)
		printf("IMAGE_INFO;    frames per second (calculated) : %.3f\n", (float)(palette->framesCount * 100 / palette->animTime));

//		write_buffer("palette.bin", paletteRawData, entry->paletteDecompSize);

	printf("IMAGE_INFO; Processing U+%04X frame: %03d\n", entry->unicodeId, 1);

	frameInfo_t* frame = (frameInfo_t*)(paletteRawData + sizeof(paletteHeader_t)); // + frameNbr * frameInfo_size
	if (bswap) bswap_frameInfo(frame);

	u8* frameRawData = tinfl_decompress_mem_to_heap(imagefontRawData + frame->frameDataOffset, frame->frameDataLength, &len, TINFL_FLAG_PARSE_ZLIB_HEADER);

	if (!frameRawData)
	{
		printf("Frame Decompress ERROR!\n");
		exit(1);
	}

	printf("FRAME_%04d;    frame_duration %d\n", 1, frame->frameTime);
	printf("FRAME_%04d;    unknown_data_2 0x%02X\n", 1, frame->unknownData2);
	printf("FRAME_%04d;    alpha_color %d\n", 1, frame->alphaMask);
	printf("FRAME_%04d;    unknown_data_3 0x%04X\n", 1, frame->unknownData3);

	u32* pal = (u32*)(paletteRawData + sizeof(paletteHeader_t) + sizeof(frameInfo_t));
	u32* rawimage = malloc(entry->imageWidth * entry->imageHeight * palette->colorChannel);

	while (len--)
	{
		rawimage[len] = pal[frameRawData[len]];
	}

	snprintf(outfile, sizeof(outfile), "out_%04X.png", entry->unicodeId);

	FILE* f = fopen(outfile, "wb");
	svpng(f, entry->imageWidth, entry->imageHeight, (u8*) rawimage, 1);
	fclose(f);

	free(rawimage);
	free(frameRawData);
	free(paletteRawData);
}

void print_usage(const char* argv0)
{
	printf("USAGE: %s filename.bin\n\n", argv0);
	return;
}

int main(int argc, char **argv)
{
	size_t len;
	u8* imagefontRawData;

	printf("\nImageFont.bin Extractor 0.1.0 - (c) 2021 by Bucanero\n\n");

	if (--argc < 1)
	{
		print_usage(argv[0]);
		return -1;
	}

	if (read_buffer(argv[1], &imagefontRawData, &len) != 0)
	{
		printf("[*] Could Not Access The File (%s)\n", argv[1]);
		return -1;
	}

	imagefontHeader_t* img_hdr = (imagefontHeader_t*) imagefontRawData;

	printf("Checking file format ...");
	int bswap = (img_hdr->bitordertype == 0x0001);

	if (!bswap)
		// LITTLE ENDIAN
		printf( "(is VITA)\n");
	else
	{
		// BIG ENDIAN
		bswap_imagefontHeader(img_hdr);
		printf("(is PS3)\n");
	}
		
	printf("Loading index ...\n");
	printf( " Number of Entries = %d (0x%X)\n", img_hdr->nbrEntries, img_hdr->nbrEntries);
	printf( " Index at Offset   = %d (0x%X)\n", img_hdr->indexStart, img_hdr->indexStart);

	indexEntry_t* index = (indexEntry_t*)(imagefontRawData + img_hdr->indexStart);

	for (int i = 0; i < img_hdr->nbrEntries; i++)
	{
		if (bswap) bswap_indexEntry(&index[i]);

		printf("----------; [%03d]\n", i);
		exportEntry(&index[i], imagefontRawData, bswap);
	}

	free(imagefontRawData);

	return 0;
}
