/* This is a Unicode library in the programming language C which deals
   with conversions to and from the UTF-8 format. */

/*
  Author: 

  Ben Bullock <benkasminbullock@gmail.com>, <bkb@cpan.org>

  Repository: 
  
  https://github.com/benkasminbullock/unicode-c
*/

#define UNICODE_UTF8_4 0x1fffff
#define UNICODE_SURROGATE_PAIR -2
#define UNICODE_TOO_BIG -7
#define UNICODE_NOT_CHARACTER -8

/* Surrogate pair zone. */

#define UNI_SUR_HIGH_START  0xD800
#define UNI_SUR_LOW_END     0xDFFF

/* Start of the "not character" range. */

#define UNI_NOT_CHAR_MIN    0xFDD0

/* End of the "not character" range. */

#define UNI_NOT_CHAR_MAX    0xFDEF

#define REJECT_FFFF(x)				\
    if ((x & 0xFFFF) >= 0xFFFE) {		\
	return UNICODE_NOT_CHARACTER;		\
    }

/* Reject code points in a certain range. */

#define REJECT_NOT_CHAR(r)					\
    if (r >= UNI_NOT_CHAR_MIN && r <= UNI_NOT_CHAR_MAX) {	\
	return UNICODE_NOT_CHARACTER;				\
    }

/* Reject surrogates. */

#define REJECT_SURROGATE(ucs2)						\
    if (ucs2 >= UNI_SUR_HIGH_START && ucs2 <= UNI_SUR_LOW_END) {	\
	/* Ill-formed. */						\
	return UNICODE_SURROGATE_PAIR;					\
    }


int32_t
ucs2_to_utf8 (int32_t ucs2, uint8_t * utf8)
{
    REJECT_FFFF(ucs2);
    if (ucs2 < 0x80) {
        utf8[0] = ucs2;
        utf8[1] = '\0';
        return 1;
    }
    if (ucs2 < 0x800) {
        utf8[0] = (ucs2 >> 6)   | 0xC0;
        utf8[1] = (ucs2 & 0x3F) | 0x80;
        utf8[2] = '\0';
        return 2;
    }
    if (ucs2 < 0xFFFF) {
        utf8[0] = ((ucs2 >> 12)       ) | 0xE0;
        utf8[1] = ((ucs2 >> 6 ) & 0x3F) | 0x80;
        utf8[2] = ((ucs2      ) & 0x3F) | 0x80;
        utf8[3] = '\0';
	REJECT_SURROGATE(ucs2);
	REJECT_NOT_CHAR(ucs2);
        return 3;
    }
    if (ucs2 <= UNICODE_UTF8_4) {
	/* http://tidy.sourceforge.net/cgi-bin/lxr/source/src/utf8.c#L380 */
	utf8[0] = 0xF0 | (ucs2 >> 18);
	utf8[1] = 0x80 | ((ucs2 >> 12) & 0x3F);
	utf8[2] = 0x80 | ((ucs2 >> 6) & 0x3F);
	utf8[3] = 0x80 | ((ucs2 & 0x3F));
        utf8[4] = '\0';
        return 4;
    }
    return UNICODE_TOO_BIG;
}
