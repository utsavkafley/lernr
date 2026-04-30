import argparse
import json
import re
import time
from pathlib import Path

import anthropic

TRANSCRIPTS_DIR = Path("data/transcripts/spanish")
PARSED_DIR = Path("data/parsed/spanish")

CONCEPT_TAXONOMY = [
    "Spanish vowel pronunciation",
    "Silent h pronunciation",
    "V pronunciation (soft b sound)",
    "Spanish pronunciation: c before e/i (/s/ or /θ/ sound)",
    "Spanish pronunciation: g before e/i (/x/ sound)",
    "Word stress rules: words ending in vowel, n, or s",
    "Word stress rules: words ending in other consonants",
    "Written accent marks for stress exceptions",
    "Monosyllabic word differentiation with accents (sí/si, mí/mi, tú/tu, sé/se)",
    "Question word accentuation (dónde/donde, cómo/como)",
    "Infinitive verb forms: -ar, -er, -ir endings",
    "Infinitive recognition and verb type classification",
    "Cognate recognition: English to Spanish",
    "Cognate conversion: -tion → -ción",
    "Cognate conversion: -tion → -ción (as infinitive verb)",
    "Cognate conversion: -ation → -ación",
    "Cognate conversion: -ion → -ión",
    "Cognate conversion: -ity/-ty → -idad/-dad",
    "Cognate conversion: -ive → -ivo/-iva",
    "Cognate conversion: -al → -al",
    "Cognate conversion: -ant/-ent → -ante/-ente",
    "Cognate conversion: -ary → -ario",
    "Cognate conversion: -ence/-ance → -encia/-ancia",
    "Cognate conversion: -ible/-able → -ible/-able",
    "Cognate conversion: -ly → -mente (adverbs)",
    "Cognate conversion: -e → -o (sincere → sincero)",
    "Cognate conversion: -tial → -cial",
    "Cognate conversion: -pose → poner (compose, suppose, oppose, impose)",
    "Cognate conversion: -tain → -tener (obtain, maintain, sustain)",
    "Cognate conversion: -tract → traer (extract, attract, contract, distract)",
    "Cognate conversion: s- + consonant cluster → es- (estado, escuela, especial)",
    "Cognate conversion: /j/ sound → /x/ sound",
    "Vowel changes in cognates",
    "Noun gender: masculine and feminine",
    "Feminine noun endings: -a, -ión, -idad",
    "Exceptions to gender rules: feminine nouns ending in -o",
    "Exceptions to gender rules: masculine nouns ending in -a",
    "Greek-origin nouns ending in -ma (masculine despite -a ending)",
    "Feminine nouns with masculine articles (el ala, el agua, el aula)",
    "Gender of nouns ending in -a but masculine (el día)",
    "Occupational nouns with gender variation (profesor/profesora)",
    "Definite articles: el, la, los, las",
    "Indefinite articles: un, una, unos, unas",
    "Article-noun gender agreement",
    "Plural formation of nouns",
    "Plural noun formation with -es",
    "Adjective gender agreement: -o/-a endings",
    "Adjective gender agreement: invariant adjectives (-e endings)",
    "Adjective number agreement",
    "Adjective gender and number agreement",
    "Adjective positioning after nouns",
    "Gender and number agreement with demonstratives",
    "Contraction al (a + el)",
    "Preposition de (of/from)",
    "Preposition en (in/on)",
    "Preposition con (with)",
    "Special forms with con: conmigo, contigo",
    "Preposition para (purpose/destination)",
    "Preposition por (cause/reason/duration)",
    "Preposition a with infinitives",
    "Prepositions: durante, sin",
    "De + noun for possession",
    "Personal pronouns after prepositions: mí, ti, él, ella",
    "Prepositional pronouns: mí vs. conmigo",
    "Present tense: regular -ar verbs",
    "Present tense: regular -er verbs",
    "Present tense: regular -ir verbs",
    "Present tense first person singular: -o ending",
    "Present tense second person informal singular: -as/-es ending",
    "Present tense third person singular: -a/-e ending",
    "Present tense third person plural: -an/-en ending",
    "Present tense nosotros form: -amos/-emos/-imos",
    "Informal tú verb forms with -s ending",
    "Present tense conjugation: ser",
    "Present tense conjugation: estar",
    "Present tense conjugation: ir",
    "Present tense conjugation: tener",
    "Present tense conjugation: venir",
    "Present tense conjugation: ver",
    "Present tense conjugation: dar (irregular doy)",
    "Present tense conjugation: saber (irregular sé)",
    "Present tense conjugation: poder",
    "Present tense conjugation: querer",
    "Irregular -go verbs: salgo, tengo, vengo, pongo",
    "Stem-changing verbs: e → ie (pensar, querer, preferir, empezar)",
    "Stem-changing verbs: o → ue (poder, dormir, volver, encontrar)",
    "Stem-changing verbs: e → i (elegir, seguir)",
    "Present tense irregular verb: ver (veo)",
    "Formal vs. informal address: tú vs. usted",
    "Formal plural address: ustedes",
    "Vosotros conjugation",
    "Vos conjugation",
    "Subject pronouns: yo, tú, él, ella, nosotros, ellos, ellas, usted, ustedes",
    "Omission of subject pronouns",
    "Emphasis with subject pronouns",
    "Masculine/feminine subject pronouns: él/ella, ellos/ellas",
    "Gender agreement with pronouns: nosotros/nosotras, ellos/ellas",
    "Ser vs. estar: characteristics vs. states",
    "Ser vs. estar with adjectives",
    "Ser vs. estar for location",
    "Ser with adjectives for permanent characteristics",
    "Estar with adjectives for temporary states",
    "Adjectives that change meaning with ser vs. estar",
    "Estar with muerto and similar expressions",
    "Ser with demonstratives (este es, estos son)",
    "Using noun phrases with ser for clarity (soy una persona + adjective)",
    "Descriptive phrases with ser",
    "Negation with no",
    "Yes/no question formation with intonation",
    "Question formation with interrogative words",
    "Interrogative: qué (what)",
    "Interrogative: cómo (how)",
    "Interrogative: dónde (where)",
    "Interrogative: cuándo (when)",
    "Interrogative: por qué (why)",
    "Interrogative: quién/quiénes (who)",
    "Interrogative: cuál (which)",
    "Interrogative: cuánto/cuánta/cuántos/cuántas (how much/many)",
    "Question word agreement with plurals",
    "Double negatives (no + nada/nadie)",
    "Negative words: nada, nadie",
    "Affirmative pronoun: algo (something)",
    "Alguien (somebody)",
    "Nadie (nobody)",
    "Nadie más (nobody else)",
    "Periphrastic obligation: tener que + infinitive",
    "Modal verb: deber + infinitive (must/should)",
    "Modal verb: poder + infinitive (can/to be able)",
    "Modal verb: querer + infinitive (to want to)",
    "Ir + a + infinitive (near future)",
    "Reflexive pronoun se (himself/herself/themselves/oneself)",
    "Reflexive pronouns: me, te, nos, se",
    "Reflexive verbs in present tense",
    "Reflexive verb: llamarse (me llamo)",
    "Reflexive verb: quedarse (to stay/remain)",
    "Reflexive verb: acordarse (to remember)",
    "Reflexive verb: enamorarse (to fall in love)",
    "Reflexive verb: darse cuenta (to realize)",
    "Reflexive verbs with stem changes in present tense",
    "Reflexive pronoun placement with conjugated verbs",
    "Reflexive verb conjugation vs. non-reflexive (quedar vs. quedarse)",
    "Present progressive: estar + gerund",
    "Gerund formation: -ar verbs → -ando",
    "Gerund formation: -er/-ir verbs → -iendo",
    "Gerunds: present participle forms (hablando, vendiendo, siendo)",
    "Direct object pronouns: lo, la, los, las",
    "Direct object pronouns: me, te, lo, la, los, las",
    "Agreement of direct object pronouns with noun gender",
    "Object pronoun placement with conjugated verbs (preverbal)",
    "Object pronoun placement with infinitives (pre- or suffix)",
    "Direct object pronouns with present progressive (lo estoy preparando / estoy preparándolo)",
    "Indirect object pronouns: me, te, le, nos, les",
    "Indirect object pronouns replacing implied prepositions",
    "Gustar construction with indirect object pronouns",
    "Parecer with indirect object pronouns",
    "Interesar with indirect object pronouns",
    "Faltar with indirect object pronouns",
    "Doler with indirect object pronouns",
    "Quedar with indirect object pronouns",
    "Indirect object pronoun les → se before direct object pronoun",
    "Double object pronouns: indirect + direct (se lo)",
    "Double object pronouns: order and placement",
    "Double object pronouns with infinitives",
    "Clarification of indirect object with a + pronoun (a él, a ella)",
    "Word order with reflexive pronouns and direct/indirect objects",
    "Personal a with direct objects",
    "Compound adjectives from nouns (preocupado from preocupación)",
    "Adjective formation from verbs: -ante/-iente",
    "Possessive adjectives: mi/mis, tu/tus, nuestro/nuestra, su/sus",
    "Possessive expressions with definite articles instead of possessives",
    "Demonstrative adjectives: este/esta/estos/estas (this/these)",
    "Demonstrative adjectives: ese/esa/esos/esas (that/those)",
    "Neuter demonstratives: esto/eso (this/that as pronouns)",
    "Neuter article lo with adjectives (lo interesante, lo fácil)",
    "Lo que (relative pronoun for 'what' in non-questions)",
    "Lo de construction (the thing about)",
    "Relative pronouns: que, quien, cual, lo que",
    "Relative clauses with prepositions",
    "Relative clauses: la semana que viene",
    "Apocopation: uno/alguno/ninguno before masculine nouns",
    "Apocopation: alguna/ninguna retention before feminine nouns",
    "Todo/todos (all/everybody)",
    "Solo (only/just)",
    "Así (like this/like that)",
    "Tan + adjective (so)",
    "Comparatives: más (more/else)",
    "Comparative structure with que (than)",
    "Más as 'anymore' in negation",
    "Intensifier: muy",
    "Un poco (a little)",
    "Verb contar: multiple meanings (to count, to tell)",
    "Volver a + infinitive (to do again)",
    "Verb + a + infinitive (comenzar a hablar, ir a + infinitive)",
    "Verb + de + infinitive (terminar de vender)",
    "Verb + gerund (seguir + gerund)",
    "Pensar + infinitive (planning/intending)",
    "Intentar + infinitive",
    "Para + infinitive (in order to)",
    "Hay (there is/there are)",
    "Había (there was/there were)",
    "Haber in infinitive form (tiene que haber)",
    "Preterite tense: regular -ar verbs",
    "Preterite tense: regular -er/-ir verbs",
    "Preterite tense: first person singular yo (-é, -í)",
    "Preterite tense: second person informal (-aste, -iste)",
    "Preterite tense: third person singular (-ó)",
    "Preterite tense: third person plural (-aron, -ieron)",
    "Preterite tense: first person plural (-amos, -imos)",
    "Preterite tense: irregular ser/ir (fui, fue, fuimos, fuiste, fueron)",
    "Preterite tense: irregular verb ver (vi, vio, viste, vimos, vieron)",
    "Preterite tense: irregular verb dar",
    "Preterite tense: irregular stem hacer → hic-",
    "Preterite tense: irregular stem poner → pus-",
    "Preterite tense: irregular stem venir → vin-",
    "Preterite tense: irregular stem traer → traj-",
    "Preterite tense: irregular stem poder → pud-",
    "Preterite tense: vowel elision in irregular verbs (fueron, trajeron, dijeron)",
    "Preterite tense: irregular verb decir",
    "Preterite tense: spelling changes (c → qu before e)",
    "Preterite tense: negation",
    "Preterite tense: question formation",
    "Preterite tense with time expressions (ayer, todavía)",
    "Reflexive verbs in preterite",
    "Direct object pronouns with preterite",
    "Indirect object pronouns with preterite",
    "Double object pronouns with preterite",
    "Imperfect tense vs. preterite tense (line vs. point in past)",
    "Imperfect tense: regular -ar verbs (-aba endings)",
    "Imperfect tense: regular -er/-ir verbs (-ía endings)",
    "Imperfect tense: irregular ir (iba, ibas, iban, íbamos)",
    "Imperfect tense: irregular ser (era, eras, eran, éramos)",
    "Imperfect tense: irregular ver (veía, veías, veían, veíamos)",
    "Imperfect tense: negation",
    "Imperfect tense for past obligation: tenía que + infinitive",
    "Reflexive verbs in imperfect tense",
    "Imperfect progressive: estaba + gerund",
    "Ir a + infinitive in imperfect tense (iba a + infinitive)",
    "Past participle formation: -ar → -ado, -er/-ir → -ido",
    "Irregular past participles (roto, muerto, abierto, dicho, hecho, visto)",
    "Past participle used as adjective with estar",
    "Past participle agreement with nouns when used as adjective",
    "Working backwards from past participles to infinitives",
    "Present perfect tense: haber + past participle",
    "Present perfect tense: haber conjugation (he, has, ha, hemos, han)",
    "Present perfect: negation",
    "Present perfect: question formation",
    "Direct object pronouns with present perfect",
    "Indirect object pronouns with present perfect",
    "Reflexive verbs with present perfect",
    "Pluperfect tense: había + past participle",
    "Reflexive verbs with past perfect",
    "Future tense: regular verbs (full infinitive + endings)",
    "Future tense endings: -é, -ás, -á, -emos, -án",
    "Future tense: irregular stems (tener → tendr-, venir → vendr-, salir → saldr-, poder → podr-, hacer → har-, decir → dir-, poner → pondr-)",
    "Future tense with reflexive verbs",
    "Direct object pronouns with future tense",
    "Negation with future tense",
    "Present tense for future reference with time expressions",
    "Conditional tense: regular verbs (-ía endings)",
    "Conditional tense: irregular verbs (same stems as irregular future)",
    "Conditional tense: irregular conditional poder → podría",
    "Conditional tense: irregular conditional hacer → haría",
    "Conditional tense: irregular conditional decir → diría",
    "Conditional tense: irregular conditional poner → pondría",
    "Conditional tense: irregular conditional venir → vendría",
    "Conditional tense: irregular conditional salir → saldría",
    "Conditional tense: debería (should)",
    "Conditional tense with gustar: me gustaría",
    "Conditional tense with -go verbs (stem contraction)",
    "Direct object pronouns with conditional",
    "Indirect object pronouns with conditional",
    "Negation with conditional tense",
    "Reflexive verb conjugation in conditional tense",
    "Conditional tense: si (if) clauses",
    "Conditional perfect: habría + past participle",
    "Conditional perfect with direct object pronouns",
    "Conditional perfect with gustar",
    "Verb family patterns: poner derivatives (componer, exponer, imponer, oponer, suponer)",
    "Verb family patterns: tener derivatives (obtener, contener, mantener, sostener, entretener)",
    "Verb family patterns: traer derivatives (extraer, atraer, contraer, distraer)",
    "Verb formation from -ación nouns (removing -ción, adding -r)",
    "Accent and spelling changes in verb stems (demostración → demostrar → mostrar)",
    "Compound word analysis (ahora: a + hora)",
    "Lo + adjective for nominalization",
    "Subjunctive mood introduction",
    "Subjunctive mood: present tense formation (-ar verbs: -o → -e shift)",
    "Subjunctive mood: present tense formation (-er/-ir verbs: -o → -a shift)",
    "Subjunctive mood: irregular forms from -go verbs",
    "Subjunctive mood: irregular verbs (ir → vaya, ser → sea, ver → vea)",
    "Subjunctive mood: present tense conjugation across all persons",
    "Subjunctive mood after quiero que / no quiero que",
    "Subjunctive mood after expressions of desire, hope, preference",
    "Subjunctive mood after impersonal expressions (es importante que, es posible que)",
    "Subjunctive mood after decir que (indirect commands)",
    "Subjunctive mood with indefinite antecedents in relative clauses",
    "Subjunctive mood with temporal expressions: cuando + future reference",
    "Subjunctive mood with indefinite expressions (como te guste, lo que prefieras)",
    "Subjunctive mood with ojalá",
    "Subjunctive mood with reflexive verbs",
    "Subjunctive mood with object pronouns",
    "Para + infinitive vs. para que + subjunctive",
    "Subjunctive avoidance strategies (es que)",
    "Hortative subjunctive: que + subjunctive for third person commands",
    "Imperative mood: informal affirmative commands (tú)",
    "Imperative mood: informal affirmative commands with -go verbs (dropping -go)",
    "Imperative mood: irregular informal command hacer → haz",
    "Imperative mood: formal affirmative commands (usted/ustedes)",
    "Imperative mood: formal commands with -go verbs",
    "Imperative mood: negative informal commands (tú) using subjunctive",
    "Imperative mood: negative formal commands",
    "Imperative mood: nosotros commands (let's)",
    "Imperative mood: negative nosotros commands",
    "Object pronoun placement in affirmative commands (suffix)",
    "Object pronoun placement in negative commands (prefix)",
    "Multiple object pronouns in commands",
    "Reflexive verbs in commands",
    "Stem-changing verbs in commands",
    "Past subjunctive (imperfect subjunctive): formation from preterite ellos form",
    "Past subjunctive: irregular verbs (fuera, dijera, trajera, tuviera, hiciera)",
    "Past subjunctive: use in conditional clauses (si yo fuera, si lo tuviera)",
    "Past subjunctive: use after past-tense trigger verbs (quería que, esperaba que)",
    "Past perfect subjunctive with si (if) clauses",
    "Subjunctive vs. indicative with si (if) clauses",
    "Present indicative vs. subjunctive in temporal clauses with future meaning",
    "Se with indirect object pronouns for unintentional events ('on me' meaning)",
    "Reflexive se with impersonal/passive meaning (se vende, se habla)",
    "Preterite tense: impersonal passive (se + preterite)",
    "Leísmo: le/les for direct objects referring to people",
    "Time expressions with hacer: hace + time period (ago)",
    "Adverbial expressions with preterite (ayer, todavía)",
    "Telling time with a las + number",
    "Vez and temporal expressions (una vez, otra vez, a la vez)",
    "Verb of motion + a + infinitive (venir a + infinitive, salir a bailar)",
    "Numbers: ocho, nueve, diez",
    "Compound sentences with pero (but)",
    "Compound sentences with cuando",
    "Compound negative sentences with y",
    "Conjunction que (mandatory in subordinate clauses)",
    "Prepositions with relative pronouns (con quien, para quien, por quien)",
    "Infinitive as subject",
    "Spanish regional dialects and variations",
    "Propia/propio for emphasis (my own)",
]

TAXONOMY_STR = "\n".join(f"- {c}" for c in CONCEPT_TAXONOMY)

SYSTEM_PROMPT = f"""You are processing Language Transfer's Complete Spanish transcripts to extract a clean Q&A dataset for a language learning app.

Your task for each transcript:
1. Read the full conversation in order.
2. Extract only exchanges where the student constructs a Spanish answer. Skip exchanges where the student answers in English (vocabulary translation checks, metalanguage questions like "what do you notice?", "where is it stressed?").
3. Use the final confirmed-correct Spanish answer - not wrong attempts that the teacher then corrects.
4. Clean up answers: strip verbal filler ("or...", "I think...", trailing "?"). Keep only the Spanish. If the student gives gender variants ("listo / lista"), use masculine as the answer and feminine as an alternate.
5. Tag each Q&A with the relevant concept(s) from the taxonomy below. Use ONLY these names. If a concept genuinely isn't covered, include it in "flagged_concepts" - do not invent a name.

Concept taxonomy:
{TAXONOMY_STR}

Return valid JSON only, no other text."""

def process_track(client, track_num, text):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"""Process Track {track_num}. Return this JSON structure:
                    {{
                    "track_number": {track_num},
                    "flagged_concepts": [],
                    "questions": [
                        {{
                        "order": 1,
                        "prompt": "<teacher question>",
                        "answer": "<clean Spanish answer>",
                        "alternate_answers": [],
                        "concepts": ["<concept from taxonomy>"]
                        }}
                    ]
                    }}
                    Transcript: {text}""",
            }
        ]
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    result = json.loads(raw)

    for q in result.get("questions", []):
        q["answer"] = q["answer"].rstrip(".").strip()
        q["alternate_answers"] = [a.rstrip(".").strip() for a in q.get("alternate_answers", [])]

    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-process already-parsed tracks")
    parser.add_argument("--track", type=int, help="Process a single track number")
    args = parser.parse_args()

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()

    if args.track:
        files = [TRANSCRIPTS_DIR / f"track_{args.track:02d}.txt"]
    else:
        files = sorted(TRANSCRIPTS_DIR.glob("track_*.txt"))

    flagged = {}
    processed = 0
    skipped = 0
    errors = []

    for txt_file in files:
        m = re.search(r"track_(\d+)", txt_file.name)
        if not m:
            continue
        num = int(m.group(1))
        if num == 1:
            continue
        
        out_path = PARSED_DIR / f"track_{num:02d}.json"
        if out_path.exists() and not args.force:
            skipped += 1
            continue
        
        print(f"Track {num:02d}...", end=" ", flush=True)
        text = txt_file.read_text(encoding="utf-8")

        try:
            result = process_track(client, num, text)

            for concept in result.get("flagged_concepts", []):
                flagged.setdefault(concept, []).append(num)

            out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            print(f"{len(result.get('questions', []))} questions")
            processed += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"ERROR: {e}")
            errors.append((num, str(e)))
    
    print(f"\nDone. {processed} processed, {skipped} skipped.")

    if flagged:
        print("\n⚠ Concepts not in taxonomy - add to CONCEPT_TAXONOMY and re-run:")
        for concept, tracks in sorted(flagged.items()):
            print(f" '{concept}' - tracks {', '.join(str(t) for t in tracks)}")

    if errors:
        print("\n✗ Errors:")
        for num, msg in errors:
            print(f"  Track {num:02d}: {msg}")


if __name__  == "__main__":
    main()