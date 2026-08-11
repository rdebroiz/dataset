# ------------------------------------------------------------------------------
# Purpose:	   Run comparison between encoded music score, at an individual or collection level
#
# Authors:	   Philippe Rigaux <philippe.rigaux@cnam.fr>
#
# Copyright:	 (c) 2026- Philippe Rigaux
# License:	   Creative commons CC BY-NC-SA 4.0, see LICENSE.md
# ------------------------------------------------------------------------------


###########
#
# Classes wrapping musicdiff operations
#
##########

class MdiffOp ():
	""" Description of MDiff operations
		op[0] is a string describing the diff: “extradel”, or “beamedit” or whatever.
		op[1] is the the AnnNote or AnnExtra or AnnVoice or AnnWhatever in the first score (None if the diff is an add)
		op[2] is the AnnNote or AnnExtra or AnnVoice or AnnWhatever in the second score (None if the diff is a delete)
		op[3] is the edit distance for this diff
	"""
	
	NOTE_INS = "noteins"
	NOTE_DEL = "notedel"
	DOT_DEL = "dotdel"
	DOT_INS = "dotins"
	ACCIDENT_DEL = "accidentdel"
	ACCIDENT_INS = "accidentins"
	ACCIDENT_EDIT = "accidentedit"
	HEAD_EDIT = "headedit"
	BEAM_INS="insbeam"
	BEAM_DEL="delbeam"
	
	EXTRA_DEL = "extradel"
	EXTRA_INS = "extrains"
	EXTRA_SYMBOL_EDIT="extrasymboledit"
	BAR_DEL = "insbar"
	BAR_INS = "delbar"
	
	LYRICS_DEL = "lyricdel"
	LYRICS_INS = "lyricedit"
	LYRICS_EDIT = "lyricins"
	LYRICS_OFFSET_EDIT="lyricoffsetedit"
	
	ARTICULATION_DEL = "delarticulation"
	ARTICULATION_INS = "insarticulation"
	EXPRESSION_INS = "insexpression"
	EXPRESSION_DEL = "delexpression"
	
	ALL_OPERATIONS = [NOTE_INS,NOTE_DEL,DOT_DEL,DOT_INS,HEAD_EDIT,
					BEAM_INS, BEAM_INS,
					ACCIDENT_DEL, ACCIDENT_INS,ACCIDENT_EDIT,
					EXTRA_DEL, EXTRA_INS, BAR_DEL, BAR_INS,
					LYRICS_DEL, LYRICS_INS, LYRICS_EDIT, LYRICS_OFFSET_EDIT,
					ARTICULATION_DEL, ARTICULATION_INS, EXPRESSION_INS, EXPRESSION_DEL]
					
	VOICE_ITEM_OPS =  [NOTE_INS,NOTE_DEL,HEAD_EDIT,
						DOT_DEL,DOT_INS,BEAM_INS,BEAM_DEL,
						ACCIDENT_DEL, ACCIDENT_INS,ACCIDENT_EDIT]
	CONTEXT_OPS = [EXTRA_DEL, EXTRA_INS, EXTRA_SYMBOL_EDIT]
	LYRICS_OPS = [LYRICS_DEL, LYRICS_INS, LYRICS_EDIT, LYRICS_OFFSET_EDIT]
	EXPRESSION_OPS = [ARTICULATION_DEL, ARTICULATION_INS, EXPRESSION_INS, EXPRESSION_DEL]
	
	def __init__(self, name, 
					first_annot_obj=None, 
					second_annot_obj=None, 
					cost=0,
					type1=None, id1=None, type2=None, id2=None) :
		self.name = name
		self.first_annot_obj = first_annot_obj
		self.second_annot_obj = second_annot_obj
		self.cost = cost
		
		self.type1 = type1
		self.id1 = id1
		self.type2 = type2
		self.id2 = id2
		
		if type1 is None:
			(self.id1, self.type1) = MdiffOp.find_type_and_id (first_annot_obj)
		if type2 is None:
			(self.id2, self.type2) = MdiffOp.find_type_and_id (second_annot_obj)
		
	@staticmethod
	def find_type_and_id (mdiff_obj):
		obj_type = str(type(mdiff_obj))
		if "AnnNote" in obj_type:
			return  MdiffOp.m21_object_id (mdiff_obj), "Note"
		elif "AnnExtra" in obj_type:
			return  MdiffOp.m21_object_id (mdiff_obj), "ReadingContext"
		else:
			return "",obj_type

	@staticmethod
	def m21_object_id (mdiff_obj):
		# musicdiff annotations now hold a weak reference to their music21 object
		m21_obj = mdiff_obj.get_object()
		return m21_obj.id if m21_obj is not None else ""
		
	def to_dict(self):
		return {
			"label": self.name,
			"first_annot_obj": str(self.first_annot_obj),
			"type1": self.type1,
			"id1": self.id1,
			"second_annot_obj": str(self.second_annot_obj),
			"type2": self.type2,
			"id2": self.id2,
			"cost": self.cost
			}

	@staticmethod
	def from_dict(op_dict):
		return MdiffOp (op_dict["label"], 
						op_dict["first_annot_obj"], 
						op_dict["second_annot_obj"], 
						op_dict["cost"],
						op_dict["type1"], op_dict["id1"],
						op_dict["type2"], op_dict["id2"]
						)

	def __repr__(self):
		return f'Op ({self.name}. ({self.first_annot_obj}, {self.second_annot_obj}). Cost: {self.cost}'

	def detail_line(self, mode='html'):
		latex_format = """<tr><td></td>
							<td></td><td></td>
							<td>{first_obj}</td>
							<td>{type1}</td>
							<td>{id1}</td>
							<td>{second_obj}</td>
							<td>{type2}</td>
							<td>{id2}</td>
							<td>{cost}</td>
							</tr>"""

		return latex_format.format(first_obj=self.first_annot_obj,
								second_obj=self.second_annot_obj,
								type1=self.type1,
								id1=self.id1,
								type2=self.type2,
								id2=self.id2,
								cost=self.cost)

class MdiffListOps ():
	""" 
		List of operations sharing the same label
	"""
	def __init__(self, label) :
		self.label = label
		self.cost = 0
		# Detailed list of ops, instances of MdiffOp
		self.ops = []
	
	def add (self, op):
		self.cost += op.cost
		self.ops.append(op)
	
	def nb_diffs(self):
		return len (self.ops)
		
	def to_dict(self):
		ops_dict = []
		for op in self.ops:
			ops_dict.append(op.to_dict())
		
		return {
			"label": self.label,
			"cost": self.cost,
			"nb_diffs": len (self.ops),
			"ops": ops_dict
			}
	
	def summary_dict (self):
		# Same as before, withou the ops array
		return {
			"label": self.label,
			"cost": self.cost,
			"nb_diffs": len (self.ops)
			}
		
	@staticmethod
	def from_dict(label, dict_list_ops):
		ops_list = MdiffListOps (label)
		#ops_list.cost = dict_list_ops["cost"]
		for dict_op in dict_list_ops["ops"]:
			ops_list.add (MdiffOp.from_dict(dict_op))
		return ops_list

	@staticmethod
	def detail_line_header(mode='html'):
		return """<tr  bgcolor='lightgrey'>
							<th>Operation</th>
							<th>Nb diffs</th>
							<th>Global cost</th>
							<th>First object</th>
							<th>Type1</th>
							<th>Id1</th>
							<th>Second object</th>
							<th>Type2</th>
							<th>Id2</th>
							<th>Cost</th>
							</tr>"""

	def detail_line(self, mode='html'):
		latex_format = """<tr bgcolor="lightgrey"><td>{op_name}</td>
							<td>{nb_diffs}</td>
							<td>{cost}</td>
							<td colspan='7'></td> </tr>"""

		return latex_format.format(op_name=self.label,
								nb_diffs=self.nb_diffs(),
								cost=self.cost)

class MdiffScoreReport():
	"""
		List of operations found in a Diff measurement 
		over one score
	"""
	DETAILED_REPORT_NAME = "results/{ref}_report.html"
	EMPTY_REPORT_NAME = "empty_report.html"

	ITEMS_SCOPE = "items"
	CONTEXT_SCOPE = "context"
	LYRICS_SCOPE = "lyrics"
	EXPRESSION_SCOPE="expressions"
	GLOBAL_SCOPE = "global"
	
	def __init__(self, score_ref, title, iiif_link) :
		self.scope = "global" # Or a specific sub-category
		self.score_ref = score_ref
		self.title = title
		self.iiif_link = iiif_link
		self.global_cost = 0
		self.nb_diffs = 0
		# Operations aggregated and indexed by label, inst. of MdiffListOps
		self.aggr_ops = {}
		# Tells whether at least on op has been added
		self.empty_report = True
		
		# Statistics on the scores
		self.pred_stats = None
		self.ground_stats = None
	
	def metric(self):
		if self.ground_stats is None:
			return "no ground", 0
		# Returns the formula and the value of the metric
		if self.scope == MdiffScoreReport.ITEMS_SCOPE:
			val = (self.nb_diffs / self.ground_stats.nb_notes) * 100
			val = '{:.2f}'.format(val)
			return "(nb diffs / nb notes)", val
		elif self.scope == MdiffScoreReport.CONTEXT_SCOPE:
			val = (self.nb_diffs / self.ground_stats.nb_context) * 100
			val = '{:.2f}'.format(val)
			return "(nb diffs / nb context)", val
		elif self.scope == MdiffScoreReport.LYRICS_SCOPE:
			if self.ground_stats.nb_lyrics != 0:
				val = (self.nb_diffs / self.ground_stats.nb_lyrics) * 100
				val = '{:.2f}'.format(val)
			else:
				val = "N/A"
			return "(nb diffs / nb lyrics)", val
		elif self.scope == MdiffScoreReport.EXPRESSION_SCOPE:
			"""if self.ground_stats.nb_lyrics != 0:
				val = (self.nb_diffs / self.ground_stats.nb_lyrics) * 100
				val = '{:.2f}'.format(val)
			else:
				val = "N/A"
			"""
			val = "todo"
			return "(nb diffs / nb expressions)", val
		else:
			return "no formula", 0
			
	def add(self, op):
		
		self.global_cost += op.cost
		self.empty_report = False
		self.nb_diffs += 1
		# General list of operations
		if not op.name in self.aggr_ops:
			self.aggr_ops[op.name] = MdiffListOps(op.name)
		self.aggr_ops[op.name].add(op)

	def sublist (self, op_categ="items"):
		# Extract a sublist of the operations, returned as a MdiffScoreReport
		sub_report = MdiffScoreReport ("", f"{op_categ} diffs", "")
		sub_report.scope = op_categ
		sub_report.ground_stats = self.ground_stats
		
		for op_name, agg_op in self.aggr_ops.items():
			if op_categ == "items" and  op_name in MdiffOp.VOICE_ITEM_OPS:
				# NB: we do no make a copy. The cost and nb_diffs
				# will be computed in the items_report
				for op in agg_op.ops:
					sub_report.add (op)
			elif op_categ == "context" and  op_name in MdiffOp.CONTEXT_OPS:
				for op in agg_op.ops:
					sub_report.add (op)
			elif op_categ == "lyrics" and  op_name in MdiffOp.LYRICS_OPS:
				for op in agg_op.ops:
					sub_report.add (op)
			elif op_categ == MdiffScoreReport.EXPRESSION_SCOPE and  op_name in MdiffOp.EXPRESSION_OPS:
				for op in agg_op.ops:
					sub_report.add (op)
		return sub_report

	def details_link (self):
		# Link to a detailed HTML file
		if self.scope=="global"and not self.empty_report:
 				return self.DETAILED_REPORT_NAME.format(ref=self.score_ref)
		else:
			return ""
			
	def to_dict(self):
		ops_dict = {}
		for label, aggr_op in self.aggr_ops.items():
			ops_dict[label] = aggr_op.to_dict()
		
		if self.pred_stats is not None:
			dict_pred_stats = self.pred_stats.to_dict()
		else:
			dict_pred_stats = None
		if self.ground_stats is not None:
			dict_ground_stats = self.ground_stats.to_dict()
		else:
			dict_ground_stats = None
			
		return {
			"score_ref": self.score_ref,
			"title": self.title,
			"iiif_link": self.iiif_link,
			"global_cost": self.global_cost,
			"nb_diffs": self.nb_diffs,
			"predicted_stats": dict_pred_stats,
			"ground_stats": dict_ground_stats,
			"aggr_ops": ops_dict
			}
	
	def summary(self):
		# A array with the summary of diffs
		summary = []
		for label, aggr_op in self.aggr_ops.items():
			summary.append(aggr_op.summary_dict())
		return summary
	def op_info(self, label):
		# Get the list of operations for a given labeel
		if label not in self.aggr_ops.keys():
			# Return a list with default values
			return MdiffListOps  (label)
		else:
			return self.aggr_ops[label]

	@staticmethod
	def from_dict(dict_report):
		report = MdiffScoreReport (dict_report["score_ref"],
						dict_report["title"],
						dict_report["iiif_link"]
		)
		report.global_cost = dict_report["global_cost"]
		report.nb_diffs = dict_report["nb_diffs"]
		report.empty_report = False
		if dict_report["predicted_stats"] is not None:
			report.pred_stats =  ScoreStats.from_dict(dict_report["predicted_stats"])
		if dict_report["ground_stats"] is not None:
			report.ground_stats =  ScoreStats.from_dict(dict_report["ground_stats"])
		for label, aggr_op in dict_report["aggr_ops"].items():
			report.aggr_ops[label] = MdiffListOps.from_dict (label, aggr_op)
		return report
	
	### Latex or HTML formatting. Maybe put somewhere else
	

	@staticmethod
	def table_header(mode='html'):
		if mode == "html":
			return "<table border='1'>"
		else:
			return """\\begin{small}
\\begin{tabular}{l|l|r|r|r}
\\textbf{Ref} & \\textbf{Title} & \\textbf{Nbs objects} &  \\textbf{Nbs diffs} & \\textbf{Metric} \\\ \hline
	"""
	

	@staticmethod
	def table_complete_header(mode='html'):
		if mode == "html":
			return "<table border='1'>"
		else:
			return """\\begin{small}
\\begin{tabular}{l|l|r|r|r|r|r|r|r|r|r}
\\textbf{Ref}& \\textbf{Title} & \\multicolumn{3}{c|}{\\textbf{Voice elements}}  & \\multicolumn{3}{c|}{\\textbf{Context elements}} & \\multicolumn{3}{c}{\\textbf{Lyrics}}\\\ 
\hline
 &  & \\textbf{Nb} &  \\textbf{Nb}  & \\textbf{Edition} & \\textbf{Nb} &  \\textbf{Nb}  & \\textbf{Edition}& \\textbf{Nb} &  \\textbf{Nb}  & \\textbf{Edition} \\\ 
 &  & \\textbf{elts} &  \\textbf{diffs} & \\textbf{Rate} & \\textbf{elts} &  \\textbf{diffs} & \\textbf{Rate} & \\textbf{elts} &  \\textbf{diffs} & \\textbf{Rate} \\\ \hline
"""
		
	@staticmethod
	def table_footer(mode='html'):
		if mode=="html":
			return "</table>"
		else:
			return """\hline
\end{tabular}
\end{small}
	"""
	
	@staticmethod
	def line_header(mode='html'):
		return """<tr><th>Ref</th><th>Title</th><th>Images</th>
							<th>Details</th>
							<th>Score info</th>
							<th>Nb diffs</th>
							<th>Metric</th>
							<th>Cost</th>
							<th>Bar del.</th>
							<th>Bar ins.</th>
							<th>Summary</th>
							</tr>"""
	
	@staticmethod
	def line_begining(score_ref=None, title=None,modde='latex',):
		score_ref = score_ref.replace("_", "\_")
		return f"{score_ref} & {title}"
		
	@staticmethod
	def line_ending(score_ref=None, title=None,modde='latex',):
		return " \\\\ \n "

	def line(self, score_ref=None, title=None, mode='html'):
		
		
		html_format = """<tr><td>{ref}</td><td>{title}</td>
		                    <td><a target='_blank' href='{iiif_link}'>link</a></td>
							<td>{details_link}</td>
							<td>{score_stats}</td>
							<td>{nb_diffs}</td>
							<td>{metric}</td>
							<td>{cost}</td>
							<td>{barins}</td>
							<td>{bardel}</td>
							<td>{summary}</td>
							</tr>"""
		latex_format = """{ref} & {title} & {nb_objs} & {nb_diffs} & {metric} \\\ 
		"""

		latex_partial_format = "& {nb_objs} & {nb_diffs} & {metric}"

	

		if self.details_link() != "":
			details_link = "<a target='_blank' href='{link}'>Ops details</a>".format(link=self.details_link())
		else:
			details_link = ""
		
		metric_form, metric_val = self.metric()

		if self.scope == MdiffScoreReport.GLOBAL_SCOPE:
			if self.ground_stats is not None:
				ground_stats = str(self.ground_stats.show('json'))
			else:
				ground_stats = 'Unknown ground ?'
		else:
			ground_stats = metric_form
			
		if mode == "html":
			return html_format.format(ref=self.score_ref, title=self.title,
								iiif_link=self.iiif_link, 
								details_link=details_link,
								score_stats=ground_stats,
								nb_diffs = self.nb_diffs,
								metric = f"{metric_val}&nbsp;%",
								cost=self.global_cost,
								noteins=self.op_info(MdiffOp.NOTE_INS).nb_diffs(),
								notedel=self.op_info(MdiffOp.NOTE_DEL).nb_diffs(),
								dotdel=self.op_info(MdiffOp.DOT_DEL).nb_diffs(),
								extrains=self.op_info(MdiffOp.EXTRA_INS).nb_diffs(),
								extradel=self.op_info(MdiffOp.EXTRA_DEL).nb_diffs(),
								barins=self.op_info(MdiffOp.BAR_INS).nb_diffs(),
								bardel=self.op_info(MdiffOp.BAR_DEL).nb_diffs(),
								summary=str(self.summary())
								)
		elif mode == "latex":
			score_ref = score_ref.replace("_", "\_")
			if self.ground_stats is not None:
				if self.scope == MdiffScoreReport.ITEMS_SCOPE:
					nb_objects = self.ground_stats.nb_notes 
				elif self.scope == MdiffScoreReport.CONTEXT_SCOPE:
					nb_objects = self.ground_stats.nb_context 
				elif self.scope == MdiffScoreReport.LYRICS_SCOPE:
					nb_objects = self.ground_stats.nb_lyrics 
			return latex_format.format(ref=score_ref, 
								title=title,
								nb_objs=nb_objects,
								nb_diffs=self.nb_diffs,
								metric = f"{metric_val} \%"
								)
		elif mode == "latex_complete":
			score_ref = score_ref.replace("_", "\_")
			if self.ground_stats is not None:
				if self.scope == MdiffScoreReport.ITEMS_SCOPE:
					nb_objects = self.ground_stats.nb_notes 
				elif self.scope == MdiffScoreReport.CONTEXT_SCOPE:
					nb_objects = self.ground_stats.nb_context 
				elif self.scope == MdiffScoreReport.LYRICS_SCOPE:
					nb_objects = self.ground_stats.nb_lyrics 
			return latex_partial_format.format(ref=score_ref, 
								title=title,
								nb_objs=nb_objects,
								nb_diffs=self.nb_diffs,
								metric = f"{metric_val} \%"
								)

class ScoreStats():
	"""
		Get statistics on an annotated score content
		
		NB: the annotation should at least feature 
					notesandrests notestaffposition signatures lyrics
	"""

	def __init__(self, annot_score= None) :
		
		self.total_symbols = 0
		# Number of notes
		self.nb_notes = 0
		# Number of symbols in notes
		self.notes_nsize = 0
		# Number and notation size of context objects
		self.nb_context = 0
		self.context_nsize = 0
		# Number and notation size of lyrics
		self.nb_lyrics = 0
		self.lyrics_nsize = 0

		if annot_score is not None:
			# Compute: the methods notation_size give us everything
			for part in annot_score.part_list:
				for bar in part.bar_list:
					for note in bar.annot_notes:
						self.notes_nsize += note.notation_size()
						#print (f"Full name suffix {note.fullNameSuffix}")
						nb_pitches = len(note.pitches)
						if nb_pitches > 1:
							print (f"This is a AnnNote with {nb_pitches} notes")
						self.nb_notes += 1
					for e in bar.extras_list:
						self.context_nsize += e.notation_size()
						self.nb_context += 1
					for lyr in bar.lyrics_list:
						self.lyrics_nsize += lyr.notation_size()
						self.nb_lyrics += 1
			self.total_symbols = self.nb_notes + self.nb_context + self.nb_lyrics

	def show(self, mode="console"):
		if mode == "console":
			print (f"""Total diffs symbols : {self.total_symbols} 
	Notes\t--  notation size = {self.notes_nsize} / nb notes = {self.nb_notes} 
	Context\t-- notation size = {self.context_nsize} / nb elements = {self.nb_context} 
	Lyrics\t-- notation size = {self.lyrics_nsize} / nb elements = {self.nb_lyrics}"""
			)
		elif mode == "json":
			return {"nb_notes": self.nb_notes,
					"notes_nsize" : self.notes_nsize,
					"nb_context": self.nb_context,
					"context_nsize": self.context_nsize,
					"nb_lyrics": self.nb_lyrics,
					"lyrics_nsize" : self.lyrics_nsize 
				}

	def format (self, score_name, mode='html'):
		html_format = """<h2>Statistics for {score_name} score</h1>
		<ul>
		<li><b>Nb notes {nb_notes}
		<li><b>Notation size for notes {notes_nsize}
		<li><b>Nb context {nb_context}
		<li><b>Notation size for context {context_nsize}
		<li><b>Nb lyrics {nb_lyrics}
		<li><b>Notation size for lyrics {lyrics_nsize}
						</ul>
		"""

		return html_format.format(
			score_name=score_name,
			nb_notes = self.nb_notes,
			notes_nsize = self.notes_nsize,
			nb_context = self.nb_context,
			context_nsize = self.context_nsize,
			nb_lyrics = self.nb_lyrics,
			lyrics_nsize = self.lyrics_nsize,
					)

	def to_dict(self):
		return {
			"total_symbols": self.total_symbols,
			"nb_notes": self.nb_notes,
			"notes_nsize": self.notes_nsize,
			"nb_context": self.nb_context,
			"context_nsize": self.context_nsize,
			"nb_lyrics": self.nb_lyrics,
			"lyrics_nsize": self.lyrics_nsize
			}

	@staticmethod
	def from_dict(dict_stats):
		stats = ScoreStats()
		stats.total_symbols = dict_stats["total_symbols"]
		stats.nb_notes = dict_stats["nb_notes"]
		stats.notes_nsize = dict_stats["notes_nsize"]
		stats.nb_context = dict_stats["nb_context"]
		stats.context_nsize = dict_stats["context_nsize"]
		stats.nb_lyrics = dict_stats["nb_lyrics"]
		stats.lyrics_nsize = dict_stats["lyrics_nsize"]
		return stats


