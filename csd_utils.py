# ------------------------------------------------------------------------------
# Purpose:	   Run comparison between encoded music score, at an individual or collection level
#
# Authors:	   Philippe Rigaux <philippe.rigaux@cnam.fr>
#
# Copyright:	 (c) 2026- Philippe Rigaux
# License:	   Creative commons CC BY-NC-SA 4.0, see LICENSE.md
# ------------------------------------------------------------------------------

import sys, os
import argparse
import re
import json
from pathlib import Path

# for XML editions
from lxml import etree

# Music analysis modules
import converter21
import music21 as m21
import musicdiff as mdif

import verovio

from musicdiff.m21utils import DetailLevel
from musicdiff.annotation import AnnScore, AnnNote, AnnMeasure
from musicdiff.comparison import Comparison
from musicdiff.visualization import Visualization

# MDiff classe
from diff_classes import MdiffOp, MdiffScoreReport, MdiffListOps, ScoreStats
from diffutilities import DiffUtilities

# Predefined dirs
OUT_DIR="results"
PREDICTED_DIR="predicted"
GROUND_TRUTH_DIR="ground_truth"

# Actions 
SINGLE_SCORE_ACTION="single"
ALL_SCORES_ACTION="all" 
BUILD_FULL_REPORT="report" 
CONVERT_GT_XML="convert_gt" 
EXTRACT_FRAGMENT="extract_fragment" 
ACTIONS = [SINGLE_SCORE_ACTION,ALL_SCORES_ACTION,
				BUILD_FULL_REPORT, CONVERT_GT_XML, EXTRACT_FRAGMENT]

def main(argv=None):
	"""
	Slightly adapted from the musicdiff code 
	by Francesco Foscarin / Greg Chapman 
	"""

	# Use the converted 21 MEI 
	converter21.register()

	current_path = os.path.dirname(os.path.abspath(__file__))
	out_dir = os.path.join(current_path, OUT_DIR)

	# Script args
	parser = argparse.ArgumentParser(description='Diff utility')
	parser.add_argument('-s', '--score', dest='score',
				   help='Name of the score file')
	parser.add_argument('-f', '--fragment', dest='fragment_id',
				   help='Id of the score fragment')
	parser.add_argument('-a', '--action', 
			dest='action', choices=ACTIONS,
			default=SINGLE_SCORE_ACTION,
			help="Action: 'single' or 'all' (score(s))")

	parser.add_argument("-d", "--details", default=["allobjects"],
			nargs="*",
			choices=["decoratednotesandrests", "otherobjects",
			"allobjects",  "style", "metadata",
			"notestaffposition", "voicing", 
			"notesandrests", "beams", "tremolos", "ornaments",
			"articulations", "ties", "slurs", "signatures",
			"directions", "barlines", "staffdetails",
			"chordsymbols", "ottavas", "arpeggios", "lyrics"],
		help="included details (can include multiple details)"
		)

	args = parser.parse_args()
	
	# Determine the combination of details
	detail: int = DetailLevel.Default
	if args.details:
		detail = 0
		for det in args.details:
			# combos
			if det == "decoratednotesandrests":
				detail |= DetailLevel.DecoratedNotesAndRests
			elif det == "otherobjects":
				detail |= DetailLevel.OtherObjects
			elif det == "allobjects":
				detail |= DetailLevel.AllObjects
			# bits not in any combo
			elif det == "style":
				detail |= DetailLevel.Style
			elif det == "voicing":
				detail |= DetailLevel.Voicing
			elif det == "metadata":
				detail |= DetailLevel.Metadata
			elif det == "notestaffposition":
				detail |= DetailLevel.NoteStaffPosition
			# bits in the DecoratedNotesAndRests combo
			elif det == "notesandrests":
				detail |= DetailLevel.NotesAndRests
			elif det == "beams":
				detail |= DetailLevel.Beams
			elif det == "tremolos":
				detail |= DetailLevel.Tremolos
			elif det == "ornaments":
				detail |= DetailLevel.Ornaments
			elif det == "articulations":
				detail |= DetailLevel.Articulations
			elif det == "ties":
				detail |= DetailLevel.Ties
			elif det == "slurs":
				detail |= DetailLevel.Slurs

			# bits in the OtherObjects combo
			elif det == "signatures":
				detail |= DetailLevel.Signatures
			elif det == "directions":
				detail |= DetailLevel.Directions
			elif det == "barlines":
				detail |= DetailLevel.Barlines
			elif det == "staffdetails":
				detail |= DetailLevel.StaffDetails
			elif det == "chordsymbols":
				detail |= DetailLevel.ChordSymbols
			elif det == "ottavas":
				detail |= DetailLevel.Ottavas
			elif det == "arpeggios":
				detail |= DetailLevel.Arpeggios
			elif det == "lyrics":
				detail |= DetailLevel.Lyrics

	if args.action == SINGLE_SCORE_ACTION:
		if args.score is None:
			sys.exit ("You must provide a file name")
		compare_single_score (args.score, detail)
	elif args.action == ALL_SCORES_ACTION:
		compare_collection (detail)
	elif args.action == BUILD_FULL_REPORT:
		build_full_report ()
	elif args.action == CONVERT_GT_XML:
		convert_gt_xml_to_mei ()
	elif args.action == EXTRACT_FRAGMENT:
		# Produce a MEI file reduced to a fragment of the score
		# It can be a page ('p3'), a system in a page ('p3-s2')
		# or a measure ('m13')
		extract_fragment (args.score, args.fragment_id)
	else:
		print (f"Unknown action {args.action}")

	return

# Typographic variants of the same lyric text (apostrophe forms, dash forms,
# space forms, spacing before punctuation) are typesetting choices, not
# recognition differences: normalize them away, on both scores, before the diff.
LYRIC_TEXT_EQUIVALENCES = str.maketrans({
	"’": "'",   # right single quotation mark
	"‘": "'",   # left single quotation mark
	"ʼ": "'",   # modifier letter apostrophe
	"—": "-",   # em dash
	"–": "-",   # en dash
	"\u00a0": " ",  # no-break space
	"\u202f": " ",  # narrow no-break space
	"\u2009": " ",  # thin space
})

def normalize_lyrics_typography(score):
	for note in score.recurse().notesAndRests:
		for lyric in note.lyrics:
			if lyric.text:
				text = lyric.text.translate(LYRIC_TEXT_EQUIVALENCES)
				text = re.sub(r" +([!?;:,.])", r"\1", text)
				text = re.sub(r"  +", " ", text).strip()
				lyric.text = text

def compare_single_score(score_name, detail):
	"""
	   Compares a predicted score (in predicted)
	   and a ground truth (in ground_truth)
	"""
	predicted_path = f"predicted/{score_name}"
	ground_truth_path = f"ground_truth/{score_name}"
	
	if not os.path.exists(predicted_path):
		raise Exception (f"File {predicted_path}  does not exist. Please check.")
	if not os.path.isfile(predicted_path):
		raise Exception (f"{predicted_path} is not a file. Please check.")
	if not os.path.exists(ground_truth_path):
		raise Exception (f"{ground_truth_path}  does not exist. Please check.")
		
	try:
		scpath = Path(score_name)
	except Exception:  # pylint: disable=broad-exception-caught
		sys.exit(f'({score_name}) is not a valid path.')
		
	
	# Get the file name without extension
	print(f"Comparing input files {predicted_path} and {ground_truth_path} ")

	predicted_score = m21.converter.parse(predicted_path, forceSource=True)
	ground_score = m21.converter.parse(ground_truth_path, forceSource=True)
	normalize_lyrics_typography(predicted_score)
	normalize_lyrics_typography(ground_score)


	# scan each score, producing an annotated wrapper
	annotated_predicted: AnnScore = AnnScore(predicted_score, detail)
	annotated_ground: AnnScore = AnnScore(ground_score, detail)
	print (f"Number of symbol in predicted : {annotated_predicted.notation_size()}")
	print (f"Number of symbol in ground : {annotated_ground.notation_size()}")

	
	diff_list, _cost = Comparison.annotated_scores_diff(annotated_predicted, 
														annotated_ground)

	oplist = []
	score_report = MdiffScoreReport(score_name, "", "")

	score_report.pred_stats = ScoreStats (annotated_predicted)
	score_report.ground_stats = ScoreStats (annotated_ground)
	
	score_report.ground_stats.show()

	if len(diff_list) > 0:
		summ: str = '\t' + DiffUtilities.oplistSummary(diff_list)
		print(summ)
		#print(summ, file=results)

	for diff in diff_list:
		op = MdiffOp (diff[0], diff[1], diff[2], diff[3])
		score_report.add (op)

	outrep = os.path.join (OUT_DIR, f"{scpath.stem}_report.json")
	with open(outrep, "w")  as rep:		
		json.dump (score_report.to_dict(), rep, indent=2 )

	Visualization.mark_diffs(predicted_score, ground_score, diff_list)
	
	# Generate and store the MusicXML file and PDF file
	outpdf1 = os.path.join (OUT_DIR, f"{scpath.stem}_predicted_diff.pdf")
	predicted_score.write("musicxml.pdf", makeNotation=False, fp=outpdf1)
	outpdf2 = os.path.join (OUT_DIR, f"{scpath.stem}_ground_diff.pdf")
	ground_score.write("musicxml.pdf", makeNotation=False, fp=outpdf2)

	print (f"See files ({outpdf1} and {outpdf2})")
	print (f"Indicators and operations list is in {outrep}")

	return
	
	mdiff.diff(predicted_score, ground_score, outpath1, outpath2,
			print_omr_ned_output=True, 
			print_text_output=True, 
			detail=detail)

def compare_collection(detail):
	"""
	   Loop on all scores and compute diffs
	"""
	with open("dataset.json") as json_data:
		dataset = json.load (json_data)
	
		# Loop on the scores, show the results
		for score in dataset["list_opus"]:
			file_name = f"{score['ref']}.musicxml"
			print (f"\n\nCompute DIFFS for score {score['title']} (file {file_name})")
			try:
				compare_single_score (file_name, detail)
			except Exception as e:
				print (f"Exception met for score {score['title']}: {e}")

def ml_training():
	"""
	   Run the ML training function
	"""
	
	# Good enough for the time being
	detail= DetailLevel.NotesAndRests

	mdiff.diff_ml_training("predicted", "ground_truth", 
				"results", detail=detail)


def build_full_report():
	"""
	  Build HTML and other file summarizing the comparison results
	"""
	REPORT_NAME = "full_report.html"
	
	# First load the dataset.json 
	with open("dataset.json") as json_data:
		dataset = json.load (json_data)
		
	# We summarize the results in a global result fie
	with open(REPORT_NAME, "w") as res_file:

		latex_complete_name =f"results/latex_complete.tex"
		latex_complete_file = open(latex_complete_name, "w")
		latex_complete_file.write (MdiffScoreReport.table_complete_header("latex"))

		latex_items_name =f"results/latex_items.tex"
		latex_items_file = open(latex_items_name, "w")
		latex_items_file.write (MdiffScoreReport.table_header("latex"))

		latex_context_name =f"results/latex_context.tex"
		latex_context_file = open(latex_context_name, "w")
		latex_context_file.write (MdiffScoreReport.table_header("latex"))

		latex_lyrics_name =f"results/latex_lyrics.tex"
		latex_lyrics_file = open(latex_lyrics_name, "w")
		latex_lyrics_file.write (MdiffScoreReport.table_header("latex"))

		res_file.write (MdiffScoreReport.table_header())
		res_file.write (MdiffScoreReport.line_header())
		# Loop on the scores, show the results
		for score in dataset["list_opus"]:
			score_ref = score['ref']
			report_file_name =f"results/{score_ref}_report.json"
			
			# Get the report file if it exists
			if os.path.exists(report_file_name):
				print(f"\tResult file exists for score {score_ref}.")
				with open(report_file_name, "r") as report_file:
					# Global report
					report = MdiffScoreReport.from_dict(json.load (report_file))
					report.title = score['title']
					report.iiif_link = score['iiif_link']
					res_file.write (report.line())
					# Voice items report
					items_report = report.sublist(op_categ=MdiffScoreReport.ITEMS_SCOPE)
					res_file.write (items_report.line())
					latex_items_file.write (
						items_report.line(score_ref, report.title, "latex"))
		
					# Context report
					context_report = report.sublist(op_categ=MdiffScoreReport.CONTEXT_SCOPE)
					res_file.write (context_report.line())
					latex_context_file.write (
						context_report.line(score_ref, report.title, "latex"))

					# Lyrics report
					lyrics_report = report.sublist(op_categ=MdiffScoreReport.LYRICS_SCOPE)
					res_file.write (lyrics_report.line())
					latex_lyrics_file.write (
						lyrics_report.line(score_ref, report.title, "latex"))


					# Expressions report
					expr_report = report.sublist(op_categ=MdiffScoreReport.EXPRESSION_SCOPE)
					res_file.write (expr_report.line())
					
					# Complete latex report with each category
					latex_complete_file.write(MdiffScoreReport.line_begining(score_ref, report.title, "latex"))
					latex_complete_file.write(items_report.line(score_ref, report.title, "latex_complete"))
					latex_complete_file.write(context_report.line(score_ref, report.title, "latex_complete"))
					latex_complete_file.write(lyrics_report.line(score_ref, report.title, "latex_complete"))
					latex_complete_file.write(MdiffScoreReport.line_ending(score_ref, report.title, "latex"))

					## OK, we also produce a detailed report dedicated
					# to the current score
					score_report_name = report.details_link()
					with open(score_report_name, "w") as score_report_file:
						score_report_file.write (MdiffScoreReport.table_header())
						score_report_file.write (MdiffListOps.detail_line_header())
						if report.pred_stats is not None:
							score_report_file.write (report.pred_stats.format("predicted"))
						if report.ground_stats is not None:
							score_report_file.write (report.ground_stats.format("ground"))
						for op_name, list_ops in report.aggr_ops.items():
							score_report_file.write (list_ops.detail_line())
							for op in list_ops.ops:
								score_report_file.write (op.detail_line())
								
						score_report_file.write (MdiffScoreReport.table_footer())
			else:
				# Default / empty values
				report = MdiffScoreReport(score['ref'], score['title'], score['iiif_link'])
				# Write the report line for this score
				res_file.write (report.line())


		res_file.write (MdiffScoreReport.table_footer())
		latex_items_file.write (MdiffScoreReport.table_footer("latex"))
		latex_context_file.write (MdiffScoreReport.table_footer("latex"))
		latex_lyrics_file.write (MdiffScoreReport.table_footer("latex"))
		latex_complete_file.write (MdiffScoreReport.table_footer("latex"))

	print (f"\nDone. Report stored in {REPORT_NAME}")


def convert_gt_xml_to_mei():
	"""
	  Convert the musicxml files from Sibelius to MEI files
	"""
	
	# First load the dataset.json 
	with open("dataset.json") as json_data:
		dataset = json.load (json_data)
		
		# Loop on the scores, show the results
		for score in dataset["list_opus"]:
			score_ref = score['ref']
			
			musicxml_name = f"./ground_truth/{score_ref}.musicxml"
			# Get the MusicXML file if it exists
			if os.path.exists(musicxml_name):
				print(f"\tMusicXML file exists for score {score_ref}")
				#with open(musicxml_name, "r") as musicxml_file:
				# Verovio converter. Works fine
				tk = verovio.toolkit()
				tk.loadFile(musicxml_name)
				mei_name = f"./ground_truth/{score_ref}.mei"
				print (f"Convert {musicxml_name} to MEI and write in {mei_name}")
				with open(mei_name, "w") as mei_file:
					mei_file.write(tk.getMEI())

	return
	
def extract_fragment (score,fragment_id):
	print (f"Extracting fragment {fragment_id} from score {score}")
	
	# Open the annotation file
	annot_file = f"iiif/{score}_annot.json"
	mei_file = f"ground_truth/{score}.mei"
	with open(annot_file) as json_annot:
		annotations = json.load (json_annot)
		# Search the annotation of the fragment
		found = False
		for annot in annotations:
			if annot['id'] == fragment_id:
				found = True
				print (f"Found annotation {fragment_id}.")
				image_url = annot['body']['resource']['source']
				frag_measures = annot['target']['resource']['selector']['value']
				print (f"Found annotation {fragment_id}. Fragment {image_url} corresponds to measures {frag_measures}")
			
				# Open MEI file and extract measures
				mei_root = etree.parse(mei_file)
				# Record the list of namespaces
				prefix_map = {"mei": "http://www.music-encoding.org/ns/mei",
						"xml": "http://www.w3.org/XML/1998/namespace"}			
				measures = mei_root.findall(".//mei:measure", prefix_map)
				for measure in measures:			
					id_qname = etree.QName('http://www.w3.org/XML/1998/namespace', 'id')
					if measure.get(id_qname) in frag_measures:
						print (f"Measure {measure.get(id_qname)} is part of the fragment")
					else:
						# Remove the measure from the document
						measure.getparent().remove (measure)
				# Clear page and system breaks
				for pb in mei_root.findall(".//mei:pb", prefix_map):	
					pb.getparent().remove (pb)
				for sb in mei_root.findall(".//mei:sb", prefix_map):	
					sb.getparent().remove(sb)
				
				# Write the MEI fragment
				extract_path = f"results/{score}_{fragment_id}.mei"
				mei_root.write (extract_path)
				print (f"Extracted MEI file has been written to {extract_path}")
		if not found:
			print (f"Unable to find annotation {fragment_id}. Check the reference")
			return
	return
		
if __name__ == "__main__":
	main()