"""EDE Reflection Space fluxuaren euskarazko testuak.

OHARRA: euskarazko testu hauek sortu berri dira; erabilera errealaren aurretik
euskaldun batek berrikusi beharko lituzke. Gakoren bat falta bada, aplikazioak
gaztelaniazko testua erabiltzen du.
"""

EDE_EU = {
    "nav_ede": "EDE hausnarketa",
    "ede_title": "EDEren hausnarketa lan profesionalaren inguruan",
    "ede_intro": (
        "Tresna honek esku-hartzea nola dokumentatzen den aztertzen laguntzen du: zer "
        "deskribatzen den, zein hitzekin eta zer geratzen den dokumentatu gabe. Ikaskuntzaren "
        "xedea jardun profesionala da, ez laguntza jasotzen duten pertsonak."
    ),
    "ede_ai_disclaimer": (
        "AAk sortutako oharrak hausnarketa profesionalerako hipotesiak dira, ez egiaztatutako "
        "ondorioak. Ez dituzte pertsonak edo profesionalak ebaluatzen, ez dute puntuaziorik "
        "ematen, ez dute sailkatzen eta ez dute epai profesionala ordezkatzen."
    ),
    "ede_privacy_notice": (
        "Pribatutasuna: IA ereduari bidali aurretik, testua aplikazioaren anonimizazio-iragazkitik "
        "pasatzen da (izenak, kontaktuak, datak, identifikatzaileak). Iragazkiak arriskua "
        "murrizten du, baina ez du anonimotasuna bermatzen: zeharkako informazioak norbait "
        "identifika dezake. Ez sartu beharrezkoak ez diren datu pertsonalik. Testua ez da datu-basean "
        "ez bilatzaile semantikoan gordetzen; saio honetan soilik geratzen da, ezabatu edo saioa itxi arte. "
        "Ez erabili benetako txostenik EDEk IA hornitzailearekin egindako tratamendua onartu arte."
    ),
    "ede_step1": "1. Testuingurua",
    "ede_programme_label": "Programa",
    "ede_doctype_label": "Dokumentu mota",
    "ede_language_label": "Azalpenen hizkuntza",
    "ede_lang_auto": "Automatikoa (dokumentuaren hizkuntza)",
    "ede_step2": "2. Aztertu beharreko testua",
    "ede_upload_label": "Kargatu testu-fitxategi bat (.txt edo .md)",
    "ede_upload_help": "Testu soileko fitxategiak baino ez dira onartzen (.txt, .md), UTF-8 kodeketan.",
    "ede_text_label": "Dokumentuaren testua",
    "ede_text_placeholder": "Itsatsi hemen hautatutako testua (beharrezkoak ez diren datu pertsonalik gabe).",
    "ede_char_counter": "{n} / {max} karaktere",
    "ede_step3": "3. Azterketa",
    "ede_analyse_button": "Aztertu jardun profesionala",
    "ede_progress": "Testua konfiguratutako IA ereduarekin aztertzen…",
    "ede_retry_button": "Saiatu berriro",
    "ede_clear_button": "Ezabatu saio honetako testua eta emaitzak",
    "ede_cleared": "Saio honetako testua eta emaitzak ezabatu dira.",
    "ede_step4": "4. Hausnarketarako oharrak",
    "ede_detected_language": "Dokumentuaren hizkuntza detektatua: {lang}",
    "ede_explained_in": "Azalpenen hizkuntza: {lang}",
    "ede_counts": "Baliozkotutako oharrak: {accepted}",
    "ede_discarded_notice": (
        "ereduak sortutako {n} oharra baztertu da, ez zutelako eskatutako formatua betetzen edo "
        "aipamena ez delako hitzez hitz agertzen aztertutako testuan."
    ),
    "ede_no_findings": (
        "Ez da oharrik egin dimentsio honetarako. Horrek ez du esan nahi hausnartzeko ezer ez dagoenik: "
        "azterketak ez du euskarri argirik aurkitu testu honetan."
    ),
    "ede_evidence_quote_loc": "Testuaren zatia ({n}. paragrafoa)",
    "ede_evidence_absence": "Testu honetan dokumentatu gabe",
    "ede_absence_caveat": (
        "Testu honetan zerbait ez agertzeak ez du frogatzen ezezaguna denik, ezta beste dokumentu "
        "batzuetan edo errealitatean ez dagoenik ere."
    ),
    "ede_ai_hypothesis_tag": "IAren hipotesia",
    "ede_observation": "Behin-behineko oharra",
    "ede_why": "Zergatik izan daitekeen garrantzitsua",
    "ede_alternative": "Ikuspegi alternatiboa",
    "ede_questions": "Elkarrizketa profesionalerako galderak",
    "ede_limitations": "Mugak: zer ezin den ondorioztatu",
    "ede_single_doc_caveat": (
        "Dokumentu bakarra aztertu da: hemen testuaren barneko kontraesanak baino ezin dira nabarmendu, "
        "ez denboran zeharreko bilakaerak edo joerak."
    ),
    "ede_feedback_header": "Balorazio profesionala",
    "ede_fb_rating_label": "Nola baloratzen duzu ohar hau?",
    "ede_fb_rating": {
        "none": "Baloratu gabe",
        "useful": "Baliagarria",
        "unsupported": "Euskarririk gabea edo garrantzirik gabea",
    },
    "ede_fb_alternative_label": "Nire interpretazio alternatiboa",
    "ede_fb_team_question_label": "Talde-bilerarako galdera",
    "ede_feedback_caption": (
        "Ohar hauek saio honetan eta deskargatzen duzun esportazioan soilik gordetzen dira. Ez dira "
        "eredua entrenatzeko, jarraibideak aldatzeko edo errendimendu-adierazle gisa erabiltzen."
    ),
    "ede_export_header": "Esportatu",
    "ede_export_caption": (
        "Esportazioak baliozkotutako oharrak eta zure oharpenak baino ez ditu jasotzen, ebidentzia-zatiekin "
        "eta mugekin. Ez du dokumentu osoa barne hartzen."
    ),
    "ede_export_json": "Deskargatu (JSON)",
    "ede_export_md": "Deskargatu (Markdown)",
    "ede_export_md_title": "Jardun profesionalari buruzko hausnarketa",
    "ede_issue_ref": "Intzidentziaren erreferentzia: #{id}",
    "ede_err_prefix": "Ezin izan da azterketa osatu.",
    "ede_errors": {
        "input_empty": "Testua hutsik dago. Itsatsi edo kargatu dokumentu bat.",
        "input_too_short": "Testua laburregia da aztertzeko.",
        "input_too_long": "Testuak onartutako gehieneko luzera gainditzen du ({max} karaktere). Hautatu zati laburrago bat.",
        "input_invalid": "Testua edo hautatutako aukerak ez dira baliozkoak.",
        "not_authorised": "Ez duzu funtzio hau erabiltzeko baimenik.",
        "provider_not_configured": "IA zerbitzua ez dago behar bezala konfiguratuta. Jakinarazi sistemaren administrazioari.",
        "provider_unavailable": "IA zerbitzua ez dago erabilgarri une honetan. Berriro saia zaitezke.",
        "output_invalid": "Ereduak eskatutako formatua betetzen ez duen erantzuna eman du. Berriro saia zaitezke.",
        "output_truncated": "Ereduaren erantzuna amaitu aurretik moztu da. Berriro saia zaitezke.",
        "busy": "Zerbitzua oso lanpetuta dago une honetan. Saiatu berriro pixka batean.",
        "rate_limited": "Orduko azterketa-mugara iritsi zara. Itxaron pixka bat eta saiatu berriro.",
        "upload_type": "Soilik .txt edo .md fitxategiak onartzen dira.",
        "upload_too_large": "Fitxategia handiegia da.",
        "upload_decode": "Ezin izan da fitxategia irakurri. Testu soila izan behar da, UTF-8 kodeketan.",
        "unknown": "Ustekabeko errore bat gertatu da.",
    },
    "ede_langs": {
        "es": "gaztelania", "eu": "euskara", "en": "ingelesa",
        "mixed": "hizkuntza nahasia", "unknown": "zehaztu gabe",
    },
    "ede_programmes": {
        "social_accommodation_bizkaia": "Gizarte-ostatuak – Bizkaia",
        "supported_housing_gipuzkoa": "Gizarte-inklusioko etxebizitzak – Gipuzkoa",
        "kulunka_bilbao": "Kulunka – Bilbo",
        "olakueta_etxea_berriz": "Olakueta Etxea – Berriz",
    },
    "ede_doctypes": {
        "follow_up_report": "Jarraipen-txostena",
        "case_note": "Kasu-oharra",
        "follow_up_diary": "Jarraipen-egunkaria",
        "interview_record": "Elkarrizketaren erregistroa",
        "social_work_report": "Gizarte-txostena",
        "referral_proposal": "Deribazio-proposamena",
        "intervention_plan": "Esku-hartze plana",
        "professional_email": "Profesionalen arteko posta elektronikoa",
        "coordination_record": "Koordinazio-erregistroa",
        "other": "Beste dokumentu profesional bat",
    },
    "ede_dims": {
        "strengths_vs_deficits": {
            "label": "Gabezietan edo indarguneetan oinarritutako hizkuntza",
            "desc": "Kontakizunak indarguneak, baliabideak, autonomia eta aurrerapausoak ere jasotzen ditu?"},
        "observation_vs_interpretation": {
            "label": "Behatzeko moduko gertaerak eta interpretazioak",
            "desc": "Zer da behagarria, zer kontatzen dute hirugarrenek eta zer da interpretazioa edo susmoa?"},
        "labels_and_language": {
            "label": "Epai profesionalean eragin dezaketen etiketak",
            "desc": "Ba al dago ikuspegia baldintzatzen duen hitzik edo orokortzerik?"},
        "stereotypes_and_assumptions": {
            "label": "Estereotipo posibleak eta ezkutuko suposizioak",
            "desc": "Idazkerak edo arrazoibideak hausnartzeko oinarri zentzuzkoa ematen duenean soilik."},
        "evidence_for_decisions": {
            "label": "Esku-hartzeko erabakiei eusten dien ebidentzia",
            "desc": "Testuan ikusten al da zertan oinarritzen diren interpretazioak, helburuak eta erabakiak?"},
        "missing_information": {
            "label": "Falta den informazioa eta ikuspegi alternatiboak",
            "desc": "Testu honetan dokumentatu gabe dagoena (ezagutzen ez dena ez bezala)."},
        "contradictions_and_change": {
            "label": "Kontraesanak eta aldaketak",
            "desc": "Dokumentu bakarrarekin, testuaren barneko kontraesanak baino ez."},
        "persons_voice": {
            "label": "Pertsonaren ahotsa, lehentasunak eta bizitza-helburuak",
            "desc": "Bere hitzak, erabakiak eta nahiak jasotzen al dira?"},
    },
}
