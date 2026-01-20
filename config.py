# -----------------------------------------  DATA EXTRACTION ---------------------------------------------------------------
search_set = {'Johannes Vermeer': ['The Milkmaid', 'The Love Letter', 'The Little Street'], 'Van Gogh': ['Self-Portrait']}
folder_path = "Data"
extracted_data_path = "Data/extracted_data.json"

# ------------------------------------------ XML VAN GOGH LETTERS -----------------------------------------------------------------------------
input_letters_van_gogh = "Data/data_vangogh/"
output_letters_van_gogh_path_eng =  "Data/letters_van_gogh_en/"
output_letters_van_gogh_path_nl = "Data/letters_van_gogh_nl/"


# ------------------------------------------ CHROMA_DB -----------------------------------------------------------------------------
chroma_db_path = './db_rijksmuseum'
collection_name = 'rijksmuseum_data'


# ------------------------------------------------- QUESTION ANSWERING ------------------------------------------------------------------
van_gogh_letters_path = "Data/letters_van_gogh_en"
vermeer_texts_path = "Data/text_vermeer/"
# -------------------------------------------------------- PREDEFINED QUESTIONS FOR EACH ARTWORK ------------------------------------------------

pred_embeddings_path = "Data/predefined_questions_embeddings.json"


PRESETS = {
    '200108369': [
        "Why did you choose such a quiet domestic moment?",
        "How did you use light to create stillness?",
        "Why portray the maid with such dignity?",
        "Why is the milk pour the painting’s focal point?",
        "Why show work as something almost heroic?",
        "Why make everyday labor feel timeless?"
    ],

   '200108370': [
        "Why frame the scene as secretly observed?",
        "How does the maid shape the letter’s meaning?",
        "Why keep the letter’s contents ambiguous?",
        "Why include music as a love symbol?",
        "Why use a stormy sea as metaphor?",
        "Why make viewers silent witnesses?"
    ],

    '200108371': [
        "Why paint an ordinary street scene?",
        "Why treat architecture like human subjects?",
        "Why emphasize cracks, bricks, and wear?",
        "Why present everyday life as meaningful?",
        "Why does the scene feel timeless?",
        "What should viewers feel here?"
    ],

    '200109794': [
        "Why focus on self-portraiture in Paris?",
        "Why experiment so boldly with color?",
        "Why depict yourself with such alert eyes?",
        "How did Paris reshape your artistic identity?",
        "Why make the brushwork so visible?",
        "What should viewers recognize in you?"
    ]
}


predefined_questions = {
    '200108369':  [
    "Why did you choose such a quiet domestic moment?",
    "How did you use light to create stillness?",
    "Why is the milk pour the painting’s focal point?",
    "What meaning did you intend behind the bread?",
    "Why portray the maid with such dignity?",
    "How did ultramarine change the mood here?",
    "Why did you remove the wall map?",
    "What role do symbolic objects play here?",
    "Why balance realism with softness and blur?",
    "How did pointillé help express texture?",
    "Why show work as something almost heroic?",
    "What story were you suggesting about daily labor?",
    "How did Dutch views of maids influence you?",
    "Why choose a low viewing angle?",
    "How intentional is the ambiguity of her expression?",
    "Why include the foot warmer at all?",
    "How did you decide what to leave unfinished?",
    "Why contrast rough bread with smooth walls?",
    "How does this painting reflect domestic virtue?",
    "Why emphasize texture over perfect clarity?",
    "How did Delft painting traditions shape this work?",
    "Why depict silence rather than conversation?",
    "How carefully planned was the diagonal composition?",
    "Why present ordinary cooking as meaningful?",
    "How did color choices guide viewers’ attention?",
    "Why keep the background so restrained?",
    "How does this differ from your later interiors?",
    "Why paint this figure as monumental?",
    "How did material textures shape the painting’s realism?",
    "Why make everyday labor feel timeless?"
]
,

    '200108370': [
    "Why did you choose to place the viewer in a dark antechamber?",
    "What effect were you seeking with the drawn-back curtain?",
    "Why frame the scene as if it is being secretly observed?",
    "How does the maid shape the emotional meaning of the letter?",
    "Why give the servant such an active, knowing role?",
    "What relationship did you imagine between the two women?",
    "Why is the mistress shown pausing rather than reading?",
    "How intentional is the ambiguity of the letter’s contents?",
    "Why include music (the cittern) as a symbol of love?",
    "How did contemporary viewers read the cittern’s symbolism?",
    "Why are the discarded slippers placed so prominently?",
    "What does the broom suggest about neglected domestic order?",
    "Why contrast wealth and intimacy in this interior?",
    "How do blue and gold guide the viewer’s eye?",
    "Why emphasize diagonals in the tiled floor?",
    "How does the floor pattern deepen the sense of space?",
    "Why include the seascape painting on the back wall?",
    "How does the stormy sea function as a metaphor for love?",
    "Why pair the seascape with a traveler landscape above it?",
    "What story connects these paintings-within-the-painting?",
    "Why make this your only work to include a seascape?",
    "How does the fireplace architecture affect the scene’s gravity?",
    "Why depict love as something private rather than public?",
    "How much did social class shape this composition?",
    "Why present love as disruptive to domestic routine?",
    "Why allow the maid to mediate desire and respectability?",
    "How carefully staged is the sense of secrecy?",
    "Why does this interior feel more theatrical than your others?",
    "What did you want viewers to feel as silent witnesses?"
],

    '200108371': [
    "Why did you choose to paint an ordinary street rather than a grand landmark?",
    "What drew you to this specific location in Delft?",
    "How did your personal connection to these houses shape the work?",
    "Why depict architecture with the care usually reserved for people?",
    "What meaning does quiet domestic life hold in this scene?",
    "Why include figures engaged in everyday tasks rather than narrative action?",
    "How do the women and children animate the stillness of the street?",
    "Why is the street shown without dramatic weather or events?",
    "How did you balance intimacy with public space?",
    "Why make the walls’ textures so tactile and prominent?",
    "What role do cracks, bricks, and wear play in the painting’s meaning?",
    "Why emphasize age and imperfection rather than renewal?",
    "How does light unify the separate architectural elements?",
    "Why is the sky given such a restrained presence?",
    "How carefully did you plan the geometry of doors and windows?",
    "Why alternate strict angles with softer human movement?",
    "What does this street reveal about Dutch civic values?",
    "Why present everyday life as worthy of contemplation?",
    "How does this work differ from your interior scenes?",
    "Why remove any obvious moral or symbolic lesson?",
    "How did viewers of your time respond to such a modest subject?",
    "Why does this scene feel timeless rather than specific to a moment?",
    "How does silence function in an outdoor painting?",
    "Why make this one of your few city views?",
    "What did painting familiar places allow you to express?",
    "How did pigment choice enhance the sense of material reality?",
    "Why let architecture dominate over narrative?",
    "How does this street reflect your sense of home?",
    "Why is the composition both stable and quietly dynamic?",
    "What did you hope viewers would feel standing before this street?"
    ],

    '200109794': [
    "Why did you turn to self-portraiture so intensively in Paris?",
    "How did financial necessity shape your choice to paint yourself?",
    "Why present yourself as a fashionable Parisian rather than a struggling artist?",
    "How consciously were you experimenting with Impressionist color here?",
    "What role do the rhythmic brushstrokes play in expressing identity?",
    "Why does the background feel as active as the face itself?",
    "How did Japanese prints influence your handling of line and color?",
    "Why avoid deep shadow in favor of vibrating color contrasts?",
    "How much of this portrait is observation versus invention?",
    "Why depict yourself with such alert, searching eyes?",
    "What does the tight framing suggest about self-scrutiny?",
    "How does the cardboard support affect the painting’s immediacy?",
    "Why favor broken brushwork over smooth modeling?",
    "How did Paris change the way you saw yourself as an artist?",
    "Why does the color palette feel experimental rather than harmonious?",
    "What emotional state were you trying to capture here?",
    "How does this self-portrait differ from your darker Dutch works?",
    "Why does the face feel solid while the surroundings dissolve?",
    "How did you use complementary colors to create tension?",
    "Why make the paint application so visible?",
    "How does this portrait function as artistic practice rather than self-analysis?",
    "Why does the expression resist clear emotion?",
    "How intentional is the sense of movement in the brushstrokes?",
    "Why portray yourself as modern rather than timeless?",
    "What were you learning from Impressionism that you later rejected?",
    "How does this self-portrait reflect ambition rather than suffering?",
    "Why does the gaze meet the viewer so directly?",
    "How did repeated self-portraits help you refine your style?",
    "Why does this image feel provisional, almost unfinished?",
    "What did you hope viewers would recognize in you as an artist?"
]
}