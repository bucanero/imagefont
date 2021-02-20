#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import struct
import zlib
import re
import ConfigParser
import png
import array

version = "v0.01, by littlebalup"

# set imagefont.bin header structure definition
bitordertype_offset = 0x00
bitordertype_length = 0x02
nbrEntries_offset = 0x02
nbrEntries_length = 0x02
indexStart_offset = 0x04
indexStart_length = 0x04
indexEntry_size   = 0x10
imagefontHeader_offset = 0x00
imagefontHeader_length = 0x08

# set index entries structure definition
paletteStart_offset = 0x00  # relative to the entry address
paletteStart_length = 0x04
paletteCompSize_offset  = 0x04  # relative to the entry address (compressed size)
paletteCompSize_length  = 0x02
paletteDecompSize_offset  = 0x06  # relative to the entry address (compressed size)
paletteDecompSize_length  = 0x02
unicodeId_offset    = 0x08  # relative to the entry address
unicodeId_length    = 0x02
imageWidth_offset   = 0x0A  # relative to the entry address
imageWidth_length   = 0x02
imageHeight_offset  = 0x0C  # relative to the entry address
imageHeight_length  = 0x02
unknownData1_offset = 0x0E  # relative to the entry address
unknownData1_length = 0x02

# set palette header structure definition
colorsCount_offset = 0x0
colorsCount_length = 0x2
colorChannel_offset = 0x2 
colorChannel_length = 0x1
framesCount_offset = 0x3
framesCount_length = 0x1
animTime_offset = 0x4
animTime_length = 0x2
paletteHeader_size = 0x6

# set frame structure definition
frameInfo_size = 0xC
frameDataOffset_length = 0x4
frameDataLength_length = 0x2
frameTime_length = 0x2
unknownData2_length = 0x01
alphaMask_length = 0x01
unknownData3_length = 0x02


def printHelp():
	print "Usage:"
	print "  %s extract <input_file> <output_dir>"%(os.path.basename(__file__))
	print "  %s repack <format> <input_dir> <output_file>"%(os.path.basename(__file__))
	print
	print " input_file    The imagefont file [path/]name to extract."
	print " output_dir    Extract path of the imagefont.bin file."
	print " format        Destination file format. Can be PS3 or VITA."
	print " input_dir     Path containing the files to repack"
	print " output_file   New repacked imagefont file [path/]name."
	print
	print "Examples:"
	print "%s extract imagefont.bin mydir"%(os.path.basename(__file__))
	print "%s repack ps3 mydir imagefont_new.bin"%(os.path.basename(__file__))
	sys.exit()


def getDataFromFile(file):
	f = open(file,"rb")
	data = f.read()
	f.close()
	return data


def writeDataToFile(data, file):
	f = open(file,"wb")
	f.write(data)
	f.close()


def decompress(compData): # as string
	decompData = zlib.decompress(compData)
	return decompData


def compress(data):
	compData = zlib.compress(data)
	return compData


def raw2numTuple(rawdata, offset, length, valsize, bitorder):
	valcount = length // valsize
	if valsize == 1: format = "%s"%("B" * valcount)
	if valsize == 2: format = "%s%s"%(bitorder, "H" * valcount)
	if valsize == 4: format = "%s%s"%(bitorder, "I" * valcount)
	return struct.unpack(format, rawdata[offset:(offset + length)])


def convertbin2png(bitorder, paletteRawData, pixelsRawData, imageWidth, imageHeight, outFile):
	colorsCountOffset = 0x0
	colorsCountLength = 0x2
	colorChannelsOffset = 0x2
	colorChannelsLength = 0x1
	framesCountOffset = 0x3
	framesCountLength = 0x1
	animTimeOffset = 0x4
	animTimeLength = 0x2

	# get color Channels count from header
	colorChannels = ord(paletteRawData[colorChannelsOffset])

	# get frames count from header
	framesCount = ord(paletteRawData[framesCountOffset])

	# calculate color map specs
	colorMapOffset = 0x6 + 0xC * framesCount
	
	rawpalette = paletteRawData[ colorMapOffset : ]

	s = [pixelsRawData[i:i+imageWidth] for i in range(0, len(pixelsRawData), imageWidth)]
	
	palette=[struct.unpack("B"*colorChannels, rawpalette[i:i+colorChannels]) for i in range(0, len(rawpalette), colorChannels)]
	
	w = png.Writer(len(s[0]), len(s), palette=palette, bitdepth=8, compression=0)
	f = open(outFile, 'wb')
	w.write(f, s)
	f.close()


def extract(infile, outdir):

	print "Loading file %s ..."%infile
	if not os.path.isfile(infile):
		sys.exit("Error : %s file not found"%infile)
	imagefontRawData = getDataFromFile(infile)

	print "Checking file format ..." ,
	bitordertype = raw2numTuple(imagefontRawData, bitordertype_offset, bitordertype_length, bitordertype_length, ">")[0]
	if bitordertype == 0x0100:
		bitorder = ">" # hi-lo
		print "(is PS3)"
	elif bitordertype == 0x0001:
		bitorder = "<" # lo-hi
		print "(is VITA)"
	else:
		sys.exit("Error : unable to determine the format.")
		
	print "Loading index ..."

	# get number of entries in the index
	nbrEntries = raw2numTuple(imagefontRawData, nbrEntries_offset, nbrEntries_length, nbrEntries_length, bitorder)[0]
	# print " Number of Entries = %i (0x%X)"%(nbrEntries, nbrEntries)

	# get index start offset
	indexStart = raw2numTuple(imagefontRawData, indexStart_offset, indexStart_length, indexStart_length, bitorder)[0]
	# print " Index at Offset   = %i (0x%X)"%(indexStart, indexStart)

	# load index to memory (in a 2D list)
	index = [] # where each entry is an index entry that list image info :)
	entryNbr = 0
	while entryNbr < nbrEntries:
		entry_offset = indexStart + entryNbr * indexEntry_size
		paletteStart = raw2numTuple(imagefontRawData, entry_offset + paletteStart_offset, paletteStart_length, paletteStart_length, bitorder)[0]
		paletteCompSize  = raw2numTuple(imagefontRawData, entry_offset + paletteCompSize_offset, paletteCompSize_length, paletteCompSize_length, bitorder)[0]
		paletteDecompSize  = raw2numTuple(imagefontRawData, entry_offset + paletteDecompSize_offset, paletteDecompSize_length, paletteDecompSize_length, bitorder)[0]
		unicodeId    = raw2numTuple(imagefontRawData, entry_offset + unicodeId_offset, unicodeId_length, unicodeId_length, bitorder)[0]
		imageWidth   = raw2numTuple(imagefontRawData, entry_offset + imageWidth_offset, imageWidth_length, imageWidth_length, bitorder)[0]
		imageHeight  = raw2numTuple(imagefontRawData, entry_offset + imageHeight_offset, imageHeight_length, imageHeight_length, bitorder)[0]
		unknownData1 = raw2numTuple(imagefontRawData, entry_offset + unknownData1_offset, unknownData1_length, unknownData1_length, bitorder)[0]
		utf8 = int("".join("{:02x}".format(ord(c)) for c in unichr(unicodeId).encode('utf-8')), 16)
		index.append([entryNbr, entry_offset, unicodeId, utf8, paletteStart, paletteCompSize, paletteDecompSize, imageWidth, imageHeight, unknownData1])
		entryNbr += 1

	# set info sub-lists address
	entryNbr = 0
	entry_offset = 1
	unicodeId = 2
	utf8 = 3
	paletteStart = 4
	paletteCompSize = 5
	paletteDecompSize = 6
	imageWidth = 7
	imageHeight = 8
	unknownData1 = 9
	
	print "Extracting image(s) ..." 

	for entry in index:
	
		print "\r  Processing U+%04X        "%entry[unicodeId] ,
	
		paletteRawData = decompress(imagefontRawData[entry[paletteStart]:(entry[paletteStart] + entry[paletteCompSize])])
		# writeDataToFile(paletteRawData, "%s/U+%04X_palette.bin"%(outdir, entry[unicodeId]))

		colorsCount = raw2numTuple(paletteRawData, colorsCount_offset, colorsCount_length, colorsCount_length, bitorder)[0]
		colorChannel = raw2numTuple(paletteRawData, colorChannel_offset, colorChannel_length, colorChannel_length, bitorder)[0]
		framesCount = raw2numTuple(paletteRawData, framesCount_offset, framesCount_length, framesCount_length, bitorder)[0]
		animTime = raw2numTuple(paletteRawData, animTime_offset, animTime_length, animTime_length, bitorder)[0]

		index[entry[entryNbr]].extend((colorsCount, colorChannel, framesCount, animTime))
		
		#set config:
		config = ConfigParser.RawConfigParser(allow_no_value=True)
		config.optionxform = str
		
		config.add_section("IMAGE_INFO")
		config.set("IMAGE_INFO", "; Note: that section is optional and for information only. It doesn't drive any configuration.")
		config.set("IMAGE_INFO", "; Info from index entry:")
		config.set("IMAGE_INFO", ";    entry number in the index : %d"%entry[entryNbr])
		config.set("IMAGE_INFO", ";    unicode code point : U+%04X"%entry[unicodeId])
		config.set("IMAGE_INFO", ";    UTF-8 hex value (calculated) : %06X"%entry[utf8])
		config.set("IMAGE_INFO", ";    image size : %d x %d"%(entry[imageWidth], entry[imageHeight]))
		config.set("IMAGE_INFO", "; Info from palette header:")
		config.set("IMAGE_INFO", ";    color count : %d"%colorsCount)
		config.set("IMAGE_INFO", ";    color channel : %d bytes (%d bits)"%(colorChannel, colorChannel*8))
		config.set("IMAGE_INFO", ";    frame count : %d"%framesCount)
		config.set("IMAGE_INFO", ";    total animation time : %.3f second(s)"%(animTime / float(100)))
		if animTime > 0 :
			config.set("IMAGE_INFO", ";    frames per second (calculated) : %.3f"%(framesCount * 100 / float(animTime)))
		
		config.add_section("INDEX_DATA")
		config.set("INDEX_DATA", "; Below value should be 0x7FFF or 0x8000 for the PS3, 0x0000 or 0x0001 for the VITA. It has unknown effect though.")
		config.set("INDEX_DATA", "unknown_data_1", "0x%04X"%entry[unknownData1])

		frameNbr = 0
		while frameNbr < framesCount:
		
			print "\r  Processing U+%04X frame%03d"%(entry[unicodeId], frameNbr + 1) ,
		
			frameInfo_offset = paletteHeader_size + frameNbr * frameInfo_size
			frameDataOffset_offset = frameInfo_offset + 0x0 
			frameDataLength_offset = frameInfo_offset + 0x4
			frameTime_offset = frameInfo_offset + 0x6
			unknownData2_offset = frameInfo_offset + 0x08
			alphaMask_offset = frameInfo_offset + 0x09
			unknownData3_offset = frameInfo_offset + 0x0A

			frameDataOffset = raw2numTuple(paletteRawData, frameDataOffset_offset, frameDataOffset_length, frameDataOffset_length, bitorder)[0]
			frameDataLength = raw2numTuple(paletteRawData, frameDataLength_offset, frameDataLength_length, frameDataLength_length, bitorder)[0]
			frameTime = raw2numTuple(paletteRawData, frameTime_offset, frameTime_length, frameTime_length, bitorder)[0]
			unknownData2 = raw2numTuple(paletteRawData, unknownData2_offset, unknownData2_length, unknownData2_length, bitorder)[0]
			alphaMask = raw2numTuple(paletteRawData, alphaMask_offset, alphaMask_length, alphaMask_length, bitorder)[0]
			unknownData3 = raw2numTuple(paletteRawData, unknownData3_offset, unknownData3_length, unknownData3_length, bitorder)[0]

			index[entry[entryNbr]].extend((frameDataOffset, frameDataLength, frameTime, unknownData2, alphaMask, unknownData3))

			frameRawData = decompress(imagefontRawData[frameDataOffset:(frameDataOffset + frameDataLength)])
			# writeDataToFile(frameRawData, "%s/U+%04X_frame%03d.bin"%(outdir, entry[unicodeId], frameNbr + 1))
			convertbin2png(bitorder, paletteRawData, frameRawData, entry[imageWidth], entry[imageHeight], "%s/U+%04X_frame%03d.png"%(outdir, entry[unicodeId], frameNbr + 1))
			
			config.add_section("FRAME_%03d"%(frameNbr + 1))
			config.set("FRAME_%03d"%(frameNbr + 1), "; Below value is the frame duration in hundredths of a second. Maximum is ‭65535‬ (0xFFFF).\n; It has no effect if only one frame.")
			config.set("FRAME_%03d"%(frameNbr + 1), "frame_duration", "%d"%frameTime)
			config.set("FRAME_%03d"%(frameNbr + 1), "; Below value should be always 0x01. It has unknown effect though.")
			config.set("FRAME_%03d"%(frameNbr + 1), "unknown_data_2", "0x%02X"%unknownData2)
			config.set("FRAME_%03d"%(frameNbr + 1), "; Below value is assumed to be the color number, from the image color palette, representing the transparent color.\n; It should be 0 to maximum 255.")
			config.set("FRAME_%03d"%(frameNbr + 1), "alpha_color", "%d"%alphaMask)
			config.set("FRAME_%03d"%(frameNbr + 1), "; Below value should be always 0x0000 (padding?). It has unknown effect though.")
			config.set("FRAME_%03d"%(frameNbr + 1), "unknown_data_3", "0x%04X"%unknownData3)
			
			frameNbr += 1
		
		print "\r  Processing U+%04X cfg     "%entry[unicodeId] ,
		
		with open("%s/U+%04X.cfg"%(outdir, entry[unicodeId]), "wb") as configfile:
			config.write(configfile)

	# set palette header info sub-lists address
	# colorsCount = 10
	# colorChannel = 11
	# framesCount = 12
	# animTime = 13

	print "\rSaving index.txt ...   "
	with open("%s/index.txt"%outdir, "w") as f:
		for entry in index:
			f.writelines("U+%04X\n"%entry[unicodeId])

	
def repack(bitorder, indir, outfile):

	# load index
	print "Loading and checking index.txt ..."
	index = []
	
	if not os.path.isfile("%s/index.txt"%indir):
		sys.exit("Error : %s/index.txt file not found"%indir)
		
	with open("%s/index.txt"%indir) as f :
		tmp = f.read().splitlines()
		
		entryNbr = 0
		l = []
		for line in tmp:
			if re.match('^U\+[0-9A-Fa-f]{4}$', line) is None :
				sys.exit("Error : wrong unicode value at line# %s. Must be U+XXXX form."%(entryNbr + 1))
			
			unicodeId = int(line[2:6], 16)
	
			if entryNbr > 0xFFFF :  # probably useless ...
				sys.exit("Error : line# %d reached. The maximum allowed lines is 65536‬."%(entryNbr + 1))
			elif unicodeId in l :
				sys.exit("Error : at line# %d, unicode U+%04X already set at line# %d."%(entryNbr + 1, unicodeId, l.index(unicodeId) + 1))
			# elif not 0xE000 <= unicodeId <= 0xF8FF :  # commented as the U+2120 is in VITA ("Letterlike Symbols" block U+2100 - U+214F)
				# sys.exit("Error : at line# %d, unicode U+%04X out of PUA range (U+E000 - U+F8FF). "%(entryNbr + 1, unicodeId))	
			
			l.append(unicodeId)
			index.append([entryNbr, unicodeId])
			
			entryNbr += 1
	
	# set info sub-lists address
	entryNbr = 0
	unicodeId = 1

	print "Compiling image(s) data ..."
	
	framesData = ""
	palettesData = ""
	
	for entry in index:
	
		print "\r  Processing U+%04X"%entry[unicodeId] ,
		
		# load cfg
		if not os.path.isfile("%s/U+%04X.cfg"%(indir, entry[unicodeId])):
			sys.exit("Error : %s/U+%04X.cfg file not found"%(indir, entry[unicodeId]))
		config = ConfigParser.RawConfigParser()
		config.read("%s/U+%04X.cfg"%(indir, entry[unicodeId]))
		
		if not config.has_section("INDEX_DATA") :
			sys.exit("Error : missing [INDEX_DATA] section in %s/U+%04X.cfg file"%(indir, entry[unicodeId]))
		elif not config.has_option("INDEX_DATA", "unknown_data_1") :
			sys.exit("Error : missing 'unknown_data_1' option in [INDEX_DATA] section in %s/U+%04X.cfg file"%(indir, entry[unicodeId]))
		elif re.match('^0x[0-9A-Fa-f]{4}$', config.get("INDEX_DATA", "unknown_data_1")) is None: 
			sys.exit("Error : wrong 'unknown_data_1' option value in [INDEX_DATA] section in %s/U+%04X.cfg file"%(indir, entry[unicodeId]))
		else :
			unknownData1 = int(config.get("INDEX_DATA", "unknown_data_1"), 16)
			
		# get frames
		frameCount = 0
		for section in config.sections() :
			if re.match('^FRAME_\d{3}$', section) is None: # skip none frame sections
				continue
			frameCount += 1
			if section != "FRAME_%03d"%frameCount :
				sys.exit("Error : [%s] section not in sequence in %s/U+%04X.cfg file"%(section, indir, entry[unicodeId]))
			if not os.path.isfile("%s/U+%04X_frame%03d.png"%(indir, entry[unicodeId], frameCount)):
				sys.exit("Error : %s/U+%04X_frame%03d.png file not found"%(indir, entry[unicodeId], frameCount))
				
		if frameCount == 0 :
			sys.exit("Error : no frame set in %s/U+%04X.cfg file"%(indir, entry[unicodeId]))
		if frameCount > 255 :
			sys.exit("Error : too much frames in %s/U+%04X.cfg file. Maximum 255 allowed frames."%(indir, entry[unicodeId]))
		
		imageWidth = 0
		imageHeight = 0
		frameNbr = 1
		colorpalette = ""
		framesinfo = ""
		animtime = 0
		while frameNbr <= frameCount :
			width = 0
			height = 1
			rows = 2
			info = 3
			r = png.Reader("%s/U+%04X_frame%03d.png"%(indir, entry[unicodeId], frameNbr))
			im = r.read()
			if imageWidth == 0 and imageHeight == 0 : # get size from first frame only
				if im[width] < 0xFFFF and im[height] < 0xFFFF: # verify size is not out of the range
					imageWidth = im[width]
					imageHeight = im[height]
				else :
					sys.exit("Error : frame image %s/U+%04X_frame%03d.png oversized (max. 65535 x 65535 pixels)."%(indir, entry[unicodeId], frameNbr))
			elif not imageWidth == im[width] and imageHeight == im[height] : # verify each frame have the same size
				sys.exit("Error : frame image %s/U+%04X_frame%03d.png have a different size than previous frame(s)."%(indir, entry[unicodeId], frameNbr))
				
			if "palette" not in im[info] :
				sys.exit("Error : %s/U+%04X_frame%03d.png is not a palettized image."%(indir, entry[unicodeId], frameNbr))
			if len(im[info]["palette"][0]) != 4 :
				sys.exit("Error : %s/U+%04X_frame%03d.png palette is not 32bits (RGBA)."%(indir, entry[unicodeId], frameNbr))

			pixelRows = list(im[rows]) # save rows . all pixels by rows as array
			pixelsData = ""  # get pixels
			for i in range(0,len(pixelRows)) :
				pixelsData = pixelsData + array.array('B', pixelRows[i]).tostring()
			# writeDataToFile(pixelsData, "%s/U+%04X_newframe%03d.bin"%(indir, entry[unicodeId], frameNbr)) # for dbg
			frameData = compress(pixelsData)
			
			rawpalette = ''.join([''.join(x) for x in [[chr(x) for x in tup] for tup in im[info]["palette"]]])
			
			if colorpalette == "" :
				colorpalette = rawpalette
			elif colorpalette != rawpalette :
				sys.exit("Error : color palette in %s/U+%04X_frame%03d.png is different than previous frame(s)."%(indir, entry[unicodeId], frameNbr))
			
			# build framesinfo
			framesinfo += struct.pack("%sI"%bitorder, imagefontHeader_length + len(framesData)) # frame offet 
			framesinfo += struct.pack("%sH"%bitorder, len(frameData)) # frame lenght
			framesinfo += struct.pack("%sH"%bitorder, config.getint("FRAME_%03d"%frameNbr, "frame_duration")) # frame time
			framesinfo += struct.pack("B", int(config.get("FRAME_%03d"%frameNbr, "unknown_data_2"), 16)) # unknown_data_2
			framesinfo += struct.pack("B", config.getint("FRAME_%03d"%frameNbr, "alpha_color")) # alpha_color
			framesinfo += struct.pack("%sH"%bitorder, int(config.get("FRAME_%03d"%frameNbr, "unknown_data_3"), 16)) # unknown_data_3

			animtime += config.getint("FRAME_%03d"%frameNbr, "frame_duration")
			
			framesData += frameData
			
			frameNbr += 1
			
		# build palette header
		palheader  = struct.pack("%sH"%bitorder, len(colorpalette) / 4) # color count
		palheader += struct.pack("B", 4) # color chanel
		palheader += struct.pack("B", frameCount) # frameCount
		palheader += struct.pack("%sH"%bitorder, animtime) # animtime

		buff = palheader + framesinfo + colorpalette
		# writeDataToFile(buff, "%s/U+%04X_newpalette.bin"%(indir, entry[unicodeId])) # for dbg
		paletteData = compress(buff)
		
		# append info to index
		entry.extend((unknownData1, imageWidth, imageHeight, frameCount, len(palettesData), len(paletteData), len(buff))) 
		                                                               # paletteStart (relative to palettes data area) / paletteCompSize / paletteDecompSize
		
		palettesData += paletteData
		
			
	# set info sub-lists address
	unknownData1 = 2
	imageWidth = 3
	imageHeight = 4
	frameCount = 5
	paletteStart = 6
	paletteCompSize = 7
	paletteDecompSize = 8
	
	# build imagefont header
	print "\rBuilding header ..."
	bitordertypeData = struct.pack("%sH"%bitorder, 0x100)
	nbrEntriesData = struct.pack("%sH"%bitorder, len(index))
	indexStartData = struct.pack("%sI"%bitorder, imagefontHeader_length + len(framesData) + len(palettesData))
	headerData = bitordertypeData + nbrEntriesData + indexStartData

	# build index data
	print "Building index ..."
	palettesStart = len(headerData) + len(framesData)
	indexData = ""
	for entry in index:
		indexData = indexData + struct.pack("%sI"%bitorder, palettesStart + entry[paletteStart]) + struct.pack("%sH"%bitorder, entry[paletteCompSize]) + struct.pack("%sH"%bitorder, entry[paletteDecompSize]) + struct.pack("%sH"%bitorder, entry[unicodeId]) + struct.pack("%sH"%bitorder, entry[imageWidth]) + struct.pack("%sH"%bitorder, entry[imageHeight]) + struct.pack("%sH"%bitorder, entry[unknownData1])

	# save to file
	print "Saving new file to %s ..."%outfile
	writeDataToFile(headerData + framesData + palettesData + indexData, "%s"%outfile)


if __name__ == "__main__":

	print "\nImagefont Tool %s\n"%version
	
	if len(sys.argv) < 2:
		printHelp()
	elif sys.argv[1].lower() == "extract" and len(sys.argv) == 4 :
		extract(sys.argv[2], sys.argv[3])
	elif sys.argv[1].lower() == "repack" and len(sys.argv) == 5 :
		if sys.argv[2].lower() == "ps3":
			bitorder = ">" # hi-lo
		elif sys.argv[2].lower() == "vita":
			bitorder = "<" # lo-hi
		else:
			printHelp()
		repack(bitorder, sys.argv[3], sys.argv[4])
	else:
		printHelp()
	
	print "\nDone!"

# end