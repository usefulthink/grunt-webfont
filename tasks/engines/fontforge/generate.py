# Based on https://github.com/FontCustom/fontcustom/blob/master/lib/fontcustom/scripts/generate.py

import fontforge
import os
import argparse
import hashlib
import json
from subprocess import call
from distutils.spawn import find_executable

# TODO: codepoints option


parser = argparse.ArgumentParser(description='Convert a directory of SVG and EPS files into a unified font file.')
parser.add_argument('input_dir', metavar='directory', type=str, help='directory of vector files')
parser.add_argument('output_dir', metavar='directory', type=str, help='output directory')
parser.add_argument('font', metavar='font', type=str, help='font name')
parser.add_argument('types', metavar='types', type=lambda s: s.split(','), help='output types')
parser.add_argument('--hashes', action='store_true', help='add hashes to file names')
parser.add_argument('--ligatures', action='store_true', help='add opentype ligatures to generated font files')
parser.add_argument('--size', type=int, default=16, help='the design- or crisp-size for the font (default: 16)')
parser.add_argument('--em', type=int, default=512, help='em-height for the font (default: 512)')
parser.add_argument('--ascent', type=int, default=448, help='height of the ascender of the font (default: 448)')
parser.add_argument('--descent', type=int, default=64, help='height of the descender of the font (default: 64)')

args = parser.parse_args()


f = fontforge.font()
f.encoding = 'UnicodeFull'
f.design_size = args.size or 16
f.em = args.em or 512
f.ascent = args.ascent or 448
f.descent = args.descent or 64

m = hashlib.md5()
cp = 0xE001

KERNING = 15


def empty_char(f, c):
	pen = f.createChar(ord(c), c).glyphPen()
	pen.moveTo((0, 0))
	pen = None


if args.ligatures:
	f.addLookup('liga', 'gsub_ligature', (), (('liga', (('latn', ('dflt')), )), ))
	f.addLookupSubtable('liga', 'liga')

for dirname, dirnames, filenames in os.walk(args.input_dir):
	for filename in filenames:
		name, ext = os.path.splitext(filename)
		filePath = os.path.join(dirname, filename)
		size = os.path.getsize(filePath)

		if ext in ['.svg', '.eps']:
			if ext in ['.svg']:
				# HACK: Remove <switch> </switch> tags
				svgfile = open(filePath, 'r+')
				svgtext = svgfile.read()
				svgfile.seek(0)

				# Replace the <switch> </switch> tags with nothing
				svgtext = svgtext.replace('<switch>', '')
				svgtext = svgtext.replace('</switch>', '')

				# Remove all contents of file so that we can write out the new contents
				svgfile.truncate()
				svgfile.write(svgtext)
				svgfile.close()

			m.update(filename + str(size) + ';')
			if args.ligatures:
				[empty_char(f, c) for c in name]
				glyph = f.createChar(cp, name)
				glyph.addPosSub('liga', tuple(name))
			else:
				glyph = f.createChar(cp)
			glyph.importOutlines(filePath)

			glyph.left_side_bearing = glyph.right_side_bearing = 0
			glyph.round()

			cp += 1

		f.autoWidth(0, 0, 512)

fontfile = args.output_dir + '/' + args.font
if args.hashes:
	fontfile += '-' + m.hexdigest()

f.fontname = args.font
f.familyname = args.font
f.fullname = args.font

if args.ligatures:
	def generate(filename):
		f.generate(filename, flags=('opentype'))
else:
	def generate(filename):
		f.generate(filename)


# TTF
generate(fontfile + '.ttf')

# Hint the TTF file
# ttfautohint is optional
if find_executable('ttfautohint'):
	call("ttfautohint --symbol --fallback-script=latn --windows-compatibility --no-info '" + fontfile + ".ttf' '" + fontfile + "-hinted.ttf' && mv '" + fontfile + "-hinted.ttf' '" + fontfile + ".ttf'", shell=True)
	f = fontforge.open(fontfile + '.ttf')

# SVG
if 'svg' in args.types:
	generate(fontfile + '.svg')

	# Fix SVG header for webkit (from: https://github.com/fontello/font-builder/blob/master/bin/fontconvert.py)
	svgfile = open(fontfile + '.svg', 'r+')
	svgtext = svgfile.read()
	svgfile.seek(0)
	svgfile.write(svgtext.replace('<svg>', '<svg xmlns="http://www.w3.org/2000/svg">'))
	svgfile.close()

scriptPath = os.path.dirname(os.path.realpath(__file__))

# WOFF
if 'woff' in args.types:
	generate(fontfile + '.woff')

# EOT
if 'eot' in args.types:
	# eotlitetool.py script to generate IE7-compatible .eot fonts
	call("python '" + scriptPath + "/../../bin/eotlitetool.py' '" + fontfile + ".ttf' --output '" + fontfile + ".eot'", shell=True)

# Delete TTF if not needed
if not 'ttf' in args.types:
	os.remove(fontfile + '.ttf')

print(json.dumps({'file': fontfile}))
