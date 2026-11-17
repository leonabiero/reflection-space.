"""
Fictional demo texts (17 November 2026 -- see DEMO.md)
========================================================

ENTIRELY FICTIONAL. Every person, family, situation and detail below was
invented for demonstrations of Pattern Review. Any resemblance to a real
person or case is a coincidence. Loaded ONLY into the separate demo
database, by services/demo_data.py.

What is in here
---------------
- 70 short practitioner notes in the style of social-work case notes:
  52 in Spanish, 18 in Basque, by eight fictional authors ("ts01".."ts08"),
  spread over the last 13 months (a few more in the most recent month, so
  even a 1-month Pattern Review has enough texts).
- Patterns that deliberately repeat over time, so Pattern Review finds
  something meaningful:
    * interpretations or opinions written as facts ("es manipuladora",
      "no tiene ningún interés");
    * directive language and warnings ("se le exige", "debe", "de lo
      contrario se informará");
    * decisions without stated reasons, and missing context ("lo de
      siempre", "situación de riesgo", "se decide derivar");
    * charged labels ("familia desestructurada", "multiproblemática",
      "absentista");
    * the person's own voice and wishes missing.
  About a sixth of the notes are written the other way (the person's own
  words, strengths, plans agreed together), for contrast.
- A few notes mention sexual orientation, gender identity, a specific
  health condition or medicine, religion or ethnic origin, so the
  anonymiser can be demonstrated on them.
- 20 fictional usefulness ratings (DEMO_RATINGS).

The Basque texts should be checked by a native speaker before being shown
to Basque-speaking staff.
"""

# (author, text) -- Spanish
_ES = [
    ("ts01", """Visita domiciliaria. Se acude al domicilio de Lucía Ortega en Barakaldo. La vivienda está desordenada y sucia. La madre es una persona manipuladora que intenta dar pena para conseguir ayudas. Se le exige que mantenga la casa limpia y que lleve a los niños al colegio todos los días. Se le advierte de que, si no cumple, se informará al Servicio de Infancia. Próxima visita en dos semanas."""),
    ("ts02", """Entrevista en despacho con Andoni Larrea. Viene por iniciativa propia. Explica que perdió el trabajo en la fábrica hace cuatro meses y que le cuesta pagar el alquiler. Dice: "Lo que más me preocupa es no poder seguir pagando el piso de mis hijos". Acordamos juntos solicitar la RGI y que él se informe en Lanbide sobre cursos de soldadura, que es lo que le interesa. Valora mucho el apoyo de su hermana, que vive cerca. Él propone volver a vernos dentro de tres semanas."""),
    ("ts03", """Familia desestructurada, conocida por los servicios desde hace años. Situación de riesgo. Se decide derivar al programa de intervención familiar. Se cierra la ayuda de urgencia. Seguimiento habitual."""),
    ("ts04", """Coordinación con el colegio de Mikel. La tutora informa de que el menor falta mucho y llega sin desayunar. El padre no se implica nada y no tiene ningún interés por la educación de su hijo. Se le cita para el jueves y se le indica que debe garantizar la asistencia diaria; de lo contrario se abrirá expediente de absentismo."""),
    ("ts05", """Seguimiento con Javier Ruiz. Tiene diagnóstico de esquizofrenia paranoide desde hace años y está en tratamiento en el centro de salud mental de Basauri. Últimamente no toma la risperidona porque dice que le da sueño. Es un usuario poco colaborador y desconfiado. Se le indica que tiene que ir sin falta a la cita con la psiquiatra la semana que viene."""),
    ("ts06", """Llamada de la vecina. Otra vez lo de siempre en casa de la familia Gómez. Se valora la situación y se decide no intervenir de momento. Se anota."""),
    ("ts01", """Entrevista con Rocío. Es una mujer conflictiva, siempre a la defensiva, y miente sobre los ingresos de su pareja. Se le explica que tiene que traer las nóminas antes del día 15 o se denegará la ayuda. Se muestra agresiva. Se le recuerda que el servicio no está para pagar sus deudas."""),
    ("ts02", """Visita a domicilio a Amaia y sus dos hijas en Sestao. La casa es pequeña pero está cuidada. Amaia cuenta que desde la separación duerme poco y que lo que más le pesa es estar sola por las tardes. Le pregunto qué le ayudaría: dice que le gustaría que las niñas fueran a la ludoteca dos tardes para poder buscar trabajo. Las niñas me enseñan sus dibujos y hablan con cariño de su abuela. Quedamos en que yo me informo de plazas en la ludoteca y ella pregunta por el grupo de apoyo del que le habló una amiga."""),
    ("ts03", """Se suspende la prestación complementaria de vivienda. Se comunica a la usuaria. Pendiente de nueva valoración."""),
    ("ts04", """Entrevista con Iker y su madre, Begoña. Iker ha contado en el instituto que es gay y desde entonces sufre burlas en clase. La madre dice que "es una fase" y que el problema es que él se busca los conflictos. Iker es un chico muy cerrado y difícil. Se acuerda derivar a psicología. Se le indica a la madre que debe acudir a todas las citas."""),
    ("ts05", """Familia multiproblemática. El padre bebe y es violento, la madre es sumisa y no protege a los menores. Los niños están descuidados. Se le exige a la madre que acuda al punto de encuentro y que se separe del padre. Si no lo hace, se valorará la retirada de la guarda."""),
    ("ts06", """Coordinación con la enfermera de Osakidetza por la situación de Pilar, que tiene 82 años y vive sola en Santurtzi. La enfermera ha observado pérdida de peso. Visito a Pilar por la tarde. Me dice que no quiere ir a una residencia: "Aquí tengo mis cosas y a mis vecinas". Hablamos de qué le cuesta más: subir la compra y cocinar. Le propongo el servicio de comida a domicilio y lo acepta para probar un mes. Su vecina del segundo, con permiso de Pilar, se ofrece a avisar si nota algo."""),
    ("ts01", """Valoración de la situación. Se mantiene el plan. Riesgo moderado. Próxima revisión en tres meses."""),
    ("ts02", """Primera entrevista con Ainhoa Etxeberria. Vive con su pareja, Marta, en un piso de alquiler en Getxo; ella misma explica que es lesbiana y que su familia no lo acepta, por lo que no tiene contacto con ellos. Acude porque Marta ha perdido el empleo y no llegan a fin de mes. Dice que lo que necesitan es "un respiro de dos o tres meses". Se tramita ayuda de emergencia social para el alquiler."""),
    ("ts03", """El usuario no quiere trabajar, prefiere vivir de las ayudas. Se le exige inscribirse en Lanbide esta semana y presentar el justificante. Se le advierte de que la próxima vez no se le renovará nada."""),
    ("ts04", """Visita al domicilio de la familia Fernández. Ambiente caótico. La madre es inmadura y no sabe poner límites. Los hijos son unos maleducados. Se observa falta de higiene. Se decide incluir a la familia en el programa de educación familiar."""),
    ("ts05", """Entrevista con Gorka, que salió del centro de menores hace seis meses. Explica que comparte piso en Bilbao con dos amigos y que trabaja los fines de semana en un bar. Me dice que su objetivo es sacarse el carné de conducir para poder trabajar de repartidor. Revisamos juntos sus gastos y él mismo propone ahorrar una parte del sueldo cada mes. Destaca que no ha tenido ningún problema con la justicia desde que salió."""),
    ("ts06", """Seguimiento de Carlos Medina, VIH positivo, en tratamiento antirretroviral en el hospital. Ha dejado de ir a las revisiones. Se le indica que es su obligación acudir y que, si no lo hace, no podremos seguir apoyándole con el transporte."""),
    ("ts01", """La menor, Irati, es una niña muy problemática y manipuladora con los adultos. Miente constantemente. En el centro escolar la tienen catalogada como conflictiva. Se mantiene el seguimiento."""),
    ("ts02", """Reunión de equipo. Se decide cambiar de profesional de referencia en el caso de la familia Sánchez. Se deriva a salud mental. Se cierra el expediente de urgencia."""),
    ("ts03", """Visita a Josu y Edurne en Portugalete. Él cuida de ella desde el ictus de hace un año. Josu dice que está agotado pero que no quiere que nadie de fuera la bañe: "Ella no querría". Edurne se comunica con gestos y asiente cuando hablamos de un centro de día dos mañanas a la semana. Acordamos probarlo y revisar en un mes cómo se sienten los dos."""),
    ("ts04", """Entrevista con la señora Carmen López. Se le explica, una vez más, que tiene que cumplir el plan. No hace caso de nada y sigue haciendo lo que quiere. Se le comunica que es la última oportunidad."""),
    ("ts05", """Caso cronificado. Familia gitana del barrio, de sobra conocida. La situación de siempre: absentismo, deudas, conflictos. Se mantiene el seguimiento."""),
    ("ts06", """Atención a Raúl. Tiene un trastorno bipolar diagnosticado y toma litio. Hoy venía alterado y exigente. Es un hombre agresivo y no se puede hablar con él. Se pospone la entrevista y se le dice que vuelva cuando esté tranquilo."""),
    ("ts01", """Entrevista con Nerea y su hijo Unai, de 9 años. Nerea cuenta que desde que le cambiaron el turno en el trabajo Unai pasa solo dos horas por la tarde. Unai dice que se aburre y que le gustaría ir al fútbol con sus amigos. Hablamos de opciones: el club del barrio tiene becas. Nerea pide ayuda para rellenar la solicitud y la hacemos juntas. También comenta que su madre podría recogerle dos días a la semana."""),
    ("ts02", """Valoración: el padre es una persona irresponsable y egoísta que solo piensa en él. Se le exige que pague la pensión de alimentos y que cumpla el régimen de visitas. Se le informa de las consecuencias legales."""),
    ("ts03", """Se deniega la solicitud de ayuda económica. Se informa a la interesada. Se archiva."""),
    ("ts04", """Sesión con Laura. Me cuenta que es bisexual y que su expareja la amenaza con "contarlo a todo el mundo" en el trabajo. Dice que lo que quiere ahora es sentirse segura y no perder el empleo. Le informo del servicio de atención a víctimas y de cómo pedir una orden de protección. Ella decide pensarlo hasta la semana que viene; respetamos su ritmo."""),
    ("ts05", """Usuaria absentista de todas las citas. Es una persona desmotivada y sin capacidad para organizarse. Se le indica que debe presentarse el lunes sin falta."""),
    ("ts06", """Llamada del centro escolar. Se valora. Se decide comunicar al Servicio de Infancia. Pendiente."""),
    ("ts01", """Entrevista de seguimiento con Fátima. Es una madre sobreprotectora que no deja que la hija haga nada sola. Se le indica que debe dejar que la niña vaya sola al colegio y que la apunte a actividades. Fátima no lo entiende."""),
    ("ts02", """Primera visita a la familia Arana. Están la madre, el padre y los dos hijos. Cada uno cuenta cómo ve la situación tras el desahucio. La madre dice que lo peor es no saber dónde van a estar en enero; el hijo mayor dice que lo que más echa de menos es su cuarto. Señalan como fortaleza que se apoyan mucho entre ellos. Acordamos priorizar la búsqueda de vivienda y que el padre pida cita en Etxebide."""),
    ("ts03", """Entrevista con Miguel Ángel, que tiene diabetes tipo 1 y no se controla bien el azúcar. Es un hombre dejado y descuidado con su salud. Se le exige que vaya a la enfermera cada semana y que lleve un registro."""),
    ("ts04", """Familia monoparental desestructurada. Mucha conflictividad. Se decide derivar al servicio especializado. Sin más."""),
    ("ts05", """La madre ha vuelto a mentir. Dice que el niño estaba enfermo, pero está claro que no le apetecía llevarle. Se le advierte de que a la tercera falta injustificada se comunicará a Fiscalía."""),
    ("ts06", """Entrevista con Rosa y su hija Sara en Basauri. Sara ha dejado de ir a clase. Le pregunto a Sara directamente qué está pasando: dice que en clase se siente sola y que le cuesta entender las matemáticas. Rosa no lo sabía y se emociona. Acordamos hablar juntas con la orientadora del instituto y buscar refuerzo. Sara propone ir ella también a la primera reunión."""),
    ("ts01", """Se mantiene el recurso. Se revisa en la próxima comisión."""),
    ("ts02", """El chico es violento y no respeta a nadie. Viene de una familia problemática y no tiene remedio. Se propone centro de día."""),
    ("ts03", """Atención a Ahmed, de religión musulmana, que pide ayuda para el alquiler. Se le explica que tiene que aprender castellano si quiere conseguir trabajo y que debe apuntarse a las clases esta semana. Se le dice que sin eso no se tramitará nada."""),
    ("ts04", """Seguimiento con Imanol. Hace tres meses dejó el consumo de alcohol con el apoyo del centro de día. Hoy dice: "Por primera vez en años me levanto con ganas". Ha retomado el contacto con su hija los domingos. Hablamos de qué le ayuda a mantenerse: el grupo de los martes y caminar junto a la ría. Él mismo propone apuntarse a un curso de cocina."""),
    ("ts05", """Visita domiciliaria a la familia Castro. La abuela es la que manda y no deja hacer nada a la madre. La madre no tiene criterio. Se le indica a la madre que tiene que imponerse y tomar ella las decisiones sobre los niños."""),
    ("ts06", """Seguimiento. Sin cambios. Se mantiene todo igual."""),
    ("ts01", """Entrevista con Sergio. Toma sertralina y lorazepam por una depresión mayor desde que murió su madre. Es un hombre muy negativo que no pone nada de su parte. Se le dice que tiene que salir de casa y buscar trabajo."""),
    ("ts02", """Madre negligente. No cuida a sus hijos y prefiere estar con el móvil. Se le exige que acuda al programa de parentalidad positiva. Se le avisa de que se informará al Servicio de Infancia de cualquier incumplimiento."""),
    ("ts03", """Coordinación con el centro de salud y visita a Teresa, que cuida de su marido con alzhéimer. Teresa explica que lo que más necesita son unas horas libres por la mañana para hacer sus recados. Le pregunto qué opina su marido; dice que a él le tranquiliza que sea siempre la misma persona. Solicitamos el servicio de ayuda a domicilio pidiendo, si es posible, que venga siempre la misma auxiliar."""),
    ("ts04", """Familia de riesgo. Se toma la decisión de reducir las visitas. Seguimos."""),
    ("ts05", """La usuaria es una persona dependiente que no quiere salir de su situación. Se le indica que debe buscar trabajo y dejar de pedir ayudas. Se le da un plazo de un mes."""),
    ("ts06", """Visita a Óscar en Barakaldo. Es un hombre trans que inició la transición hace un año. Su padre no lo acepta y le ha echado de casa. Óscar está deprimido y es inestable. Se le tramita plaza en el albergue."""),
    ("ts01", """Se cambia el plan de intervención. Se informa al equipo."""),
    ("ts02", """Entrevista con Patricia. Explica que quiere recuperar la custodia de sus hijos y qué ha hecho estos meses: un curso de auxiliar de geriatría y un trabajo de media jornada. Me pide que le diga sinceramente qué le falta. Repasamos juntas el plan del juzgado. Ella señala que lo que más le cuesta es el transporte a las visitas en Bilbao; buscamos una solución con el bono."""),
    ("ts03", """El menor es un caso perdido, ya no se puede hacer nada con él. Familia sin recursos personales. Se le exige a la madre que firme el acuerdo de colaboración."""),
    ("ts04", """La señora es exagerada y se queja de todo. Se le explica que tiene que tener paciencia y que el servicio no puede hacer más. Se cierra la demanda."""),
]

# (author, text) -- Basque
_EU = [
    ("ts07", """Etxeko bisita Bilbon. Ama, Miren, oso pertsona arduragabea da eta ez du bere seme-alaben ardurarik hartzen. Etxea zikin eta nahasia dago. Hurrengo astean haurrak ikastetxera eraman behar dituela esan zaio; bestela, Haurren Zerbitzuari jakinaraziko zaio."""),
    ("ts08", """Elkarrizketa Jonekin. Bere kabuz etorri da. Lana galdu duela eta alokairua ordaintzeko arazoak dituela azaldu du. Bere hitzetan: "Nire alabak ez du ezer jakin behar, ez dut kezkatu nahi". Elkarrekin erabaki dugu DSBE eskatzea eta Lanbiden ikastaro bati buruz galdetzea, berak hori nahi duelako. Hiru aste barru berriro elkartuko gara."""),
    ("ts07", """Egoera ezaguna. Betiko arazoak. Familia-esku-hartzeko programara bideratzea erabaki da. Jarraipena."""),
    ("ts08", """Familia desegituratua. Aita alkoholikoa eta bortitza da. Ama ez da gai seme-alabak babesteko. Haurrak zaindu gabe daude. Amari eskatu zaio aitarengandik banantzeko."""),
    ("ts07", """Jarraipena Koldorekin. Eskizofrenia diagnostikoa du eta osasun mentaleko zentroan tratamendua jasotzen du. Azken asteetan ez ditu botikak hartzen. Datorren astean psikiatrarengana joan behar duela esan zaio, derrigorrez."""),
    ("ts08", """Etxeko bisita Leireri eta bere bi semeei Barakaldon. Leirek kontatu du banandu zenetik gauetan ez duela lorik egiten. Zer lagunduko liokeen galdetu diot: arratsaldetan lana bilatzeko denbora izatea. Semeek aitonari buruz hitz egin dute pozik. Ludotekako plazei buruz informatuko naizela adostu dugu, eta berak lagun batek aipatu zion laguntza-taldeari buruz galdetuko du."""),
    ("ts07", """Erabiltzaileak ez du lan egin nahi, laguntzekin bizitzea nahiago du. Aste honetan Lanbiden izena eman eta egiaztagiria ekarri behar duela esan zaio. Hurrengoan ez zaiola ezer berrituko ohartarazi zaio."""),
    ("ts08", """Etxebizitzarako prestazio osagarria eten da. Erabiltzaileari jakinarazi zaio. Balorazio berriaren zain."""),
    ("ts07", """Elkarrizketa Ekaitzekin eta bere amarekin. Ekaitzek institutuan gaya dela esan du, eta harrezkero ikaskideek iseka egiten diote. Amak dio "pasatuko zaiola". Ekaitz mutil itxia eta zaila da. Psikologiara bideratzea adostu da."""),
    ("ts08", """Koordinazioa Osakidetzako erizainarekin Karmeni buruz, Santurtzin bakarrik bizi baita. Bisitan Karmenek esan dit ez duela egoitzara joan nahi: "Hemen ditut nire gauzak eta auzokideak". Erosketak igotzea eta sukaldatzea kostatzen zaizkiola dio. Etxez etxeko janari-zerbitzua hilabetez probatzea onartu du."""),
    ("ts07", """Ama zabarra da. Ez ditu seme-alabak zaintzen eta mugikorrarekin egotea nahiago du. Gurasotasun positiboko programara joan behar duela eskatu zaio."""),
    ("ts08", """Jarraipena. Aldaketarik ez. Dena berdin mantentzen da."""),
    ("ts07", """Adingabea oso gatazkatsua eta manipulatzailea da helduekin. Etengabe gezurrak esaten ditu. Amari esan zaio mugak jarri behar dizkiola eta zorrotzagoa izan behar duela."""),
    ("ts08", """Elkarrizketa Aitorrekin. Duela hiru hilabete alkohola edateari utzi zion, eguneko zentroaren laguntzarekin. Gaur esan du: "Urte askoren ondoren, gogoz jaikitzen naiz". Igandeetan alabarekin harremana berreskuratu du. Zerk laguntzen dion hitz egin dugu: asteartetako taldeak eta itsasadarraren ondoan paseatzeak. Berak proposatu du sukaldaritza-ikastaro batean izena ematea."""),
    ("ts07", """Bisita Joseba Uriarterekin. Nahaste bipolarra du eta litioa hartzen du. Gaur oso urduri eta zakar zegoen. Gizon oldarkorra da eta ezin da berarekin hitz egin. Elkarrizketa atzeratu da."""),
    ("ts08", """Arrisku-familia. Bisitak murriztea erabaki da. Aurrera."""),
    ("ts07", """Emakumea beti kexatzen da eta dena puztu egiten du. Pazientzia izan behar duela eta zerbitzuak ezin duela gehiago egin azaldu zaio. Eskaera itxi da."""),
    ("ts08", """Elkarrizketa Itziarrekin eta bere alaba Uxuerekin. Uxuek klasera joateari utzi dio. Uxueri zuzenean galdetu diot zer gertatzen den: klasean bakarrik sentitzen dela eta matematika asko kostatzen zaiola. Itziarrek ez zekien. Orientatzailearekin elkarrekin hitz egitea adostu dugu, eta Uxuek lehen bilerara joan nahi duela esan du."""),
]

# Days ago for each text, in order: eight in the most recent month (so a
# 1-month Pattern Review has more than the minimum of 5 texts), the rest
# spread evenly back to about 13 months (395 days), always inside the
# 15 months the texts are kept.
_RECENT_DAYS = [2, 5, 8, 12, 16, 19, 23, 27]
_OLDEST_DAY = 395


def _schedule(count):
    rest = count - len(_RECENT_DAYS)
    start = 33
    spread = [start + round(k * (_OLDEST_DAY - start) / max(1, rest - 1)) for k in range(rest)]
    return _RECENT_DAYS + spread


def _merge():
    """Spanish and Basque notes interleaved (about one in four in Basque),
    so both languages appear across the whole 13 months."""
    es, eu = list(_ES), list(_EU)
    merged = []
    i = 0
    while es or eu:
        if eu and (i % 4 == 2 or not es):
            author, text = eu.pop(0)
            merged.append({"author": author, "language": "Euskera", "text": text})
        else:
            author, text = es.pop(0)
            merged.append({"author": author, "language": "Español", "text": text})
        i += 1
    for item, days in zip(merged, _schedule(len(merged))):
        item["days_ago"] = days
        item["hour_offset"] = (days * 7) % 9
    return merged


DEMO_TEXTS = _merge()

# 20 fictional usefulness ratings: (days ago, rating 1-5, author).
DEMO_RATINGS = [
    (4, 5, "ts02"), (9, 4, "ts06"), (15, 4, "ts01"), (26, 5, "ts08"),
    (41, 3, "ts05"), (55, 4, "ts03"), (70, 5, "ts04"), (88, 4, "ts07"),
    (104, 4, "ts02"), (121, 3, "ts06"), (140, 5, "ts01"), (162, 4, "ts05"),
    (185, 4, "ts08"), (207, 5, "ts03"), (230, 3, "ts04"), (256, 4, "ts07"),
    (281, 5, "ts02"), (310, 4, "ts06"), (338, 4, "ts01"), (372, 3, "ts05"),
]
