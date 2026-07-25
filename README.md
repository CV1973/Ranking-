### README.md - AI Infrastructure Ranking v7.45.4-US

Dieses Modell ist ein regelbasiertes Scoring-System zur Bewertung von Unternehmen im AI-Infrastruktur-Zyklus. Es wurde speziell für den aktuellen CapEx-Boom bis Q4 2027 entwickelt und bewertet 37 US-Listings und ADRs aus dem Bereich Halbleiter, Server, Power, Networking und Cloud.

#### 1. Axiomatische Annahmen

Das Modell basiert auf einem einzigen Axiom: *CAPEX BOOM BIS Q4 2027 - EMPFÄNGER GEWINNEN*. 

Aus diesem Axiom folgen drei operative Regeln. Erstens wird zwischen Empfängern und Spendern unterschieden. Empfänger sind Unternehmen die direkt vom Aufbau von Rechenzentren profitieren. Dazu zählen Chip-Hersteller, Equipment-Lieferanten, Server-Bauer und Energieversorger. Spender sind Hyperscaler und Cloud-Plattformen die das Kapital investieren. Neutrale Werte haben keinen direkten CapEx-Hebel.

Zweitens wird die Operating Margin als wichtigster Faktor definiert. Im Skalierungszyklus setzt sich durch wer operative Hebel hat. Daher erhält Operating Margin bei allen drei Typen eine Gewichtung von 30%.

Drittens wird die Gewichtung der restlichen KPIs an den Typ angepasst. Für Empfänger steht Wachstum im Vordergrund mit 30% Gewichtung. Für Spender steht Cash-Generierung im Vordergrund mit 25% Gewichtung auf FCF-Marge. Für Empfänger ist FCF mit 5% fast irrelevant.

Zusätzlich erhält jeder Typ einen fixen Bias. Empfänger bekommen +10 Punkte, Spender -10 Punkte, Neutrale 0 Punkte. Dieser Bias bildet die strukturelle Bevorzugung im CapEx-Zyklus ab.

#### 2. Methodik und Berechnung

Das Scoring läuft in vier Schritten ab. 

Im ersten Schritt werden alle 6 Pflicht-KPIs über das gesamte Universum von 37 Werten normalisiert. Der Wertebereich liegt zwischen 0 und 1. Bei Forward KGV und EV/EBITDA wird invertiert, da niedrige Werte besser sind.

Die 6 Pflicht-KPIs sind: Forward KGV, EV/EBITDA, Umsatzwachstum, Bruttomarge, Operating Margin, FCF Marge. Die Daten werden per Yahoo Finance geladen. Fehlende Werte führen zu einem Abschlag über den Datenqualitätsfaktor.

Im zweiten Schritt wird der Finanzscore berechnet. Das ist die gewichtete Summe aller normierten KPIs multipliziert mit 100. Die Gewichtung unterscheidet sich je nach Typ.

Empfänger: KGV 10%, EV 5%, Wachstum 30%, Brutto 10%, OpMargin 30%, FCF 5%  
Spender: KGV 15%, EV 10%, Wachstum 5%, Brutto 15%, OpMargin 30%, FCF 25%  
Neutral: KGV 15%, EV 15%, Wachstum 15%, Brutto 15%, OpMargin 20%, FCF 20%

Im dritten Schritt wird der Roh-Gesamtscore gebildet. Der Finanzscore wird mit 0.9 multipliziert um Raum für den Bias zu schaffen.

Im vierten Schritt erfolgt der finale Gesamtscore. Der Roh-Score wird mit dem Datenqualitätsfaktor gewichtet. Formel: 0.3 + 0.7 _ Datenqualität. Bei 6 von 6 KPIs ist der Faktor 1.0. Bei 3 von 6 KPIs ist er 0.65. Danach wird der Capex-Bias addiert.

Aus dem Gesamtscore wird ein Investment Rating abgeleitet. Ab 80 ist es Strong Buy, ab 65 Buy, ab 45 Hold, darunter Sell. Bei fehlenden Daten lautet das Rating N/A - Daten fehlen.

#### 3. Praxisbeispiel 1: Micron Technology MU - Empfänger

MU ist ein klassischer Empfänger im Segment Memory und HBM. 

Annahmen: KGV 12.0, EV/EBITDA 8.0, Wachstum 45%, Bruttomarge 40%, OpMargin 25%, FCF Marge 15%. Alle Daten vorhanden.

Nach Normierung über das Universum ergibt sich: KGV 0.80, EV 0.85, Wachstum 0.95, Brutto 0.70, OpMargin 0.75, FCF 0.60.

Berechnung Finanzscore mit Empfänger-Gewichtung:  
0.80_0.10 + 0.85_0.05 + 0.95_0.30 + 0.70_0.10 + 0.75_0.30 + 0.60_0.05 = 0.7325  
Finanzscore = 73.25

Roh-Score = 73.25 _ 0.9 = 65.93  
Datenqualität = 1.0, Faktor = 1.0  
Gesamtscore = 65.93 _ 1.0 + 10 Bias = 75.9

Ergebnis: 75.9 Buy. Treiber sind das hohe Wachstum, die starke OpMargin und der Empfänger-Bonus.

#### 4. Praxisbeispiel 2: Amazon AMZN - Spender

AMZN ist ein klassischer Spender im Segment Cloud und AI Platform.

Annahmen: KGV 35.0, EV/EBITDA 18.0, Wachstum 12%, Bruttomarge 48%, OpMargin 11%, FCF Marge 8%. Alle Daten vorhanden.

Nach Normierung über das Universum ergibt sich: KGV 0.30, EV 0.25, Wachstum 0.40, Brutto 0.85, OpMargin 0.30, FCF 0.35.

Berechnung Finanzscore mit Spender-Gewichtung:  
0.30_0.15 + 0.25_0.10 + 0.40_0.05 + 0.85_0.15 + 0.30_0.30 + 0.35_0.25 = 0.395  
Finanzscore = 39.50

Roh-Score = 39.50 _ 0.9 = 35.55  
Datenqualität = 1.0, Faktor = 1.0  
Gesamtscore = 35.55 * 1.0 - 10 Bias = 25.6

Ergebnis: 25.6 Sell. Treiber sind das hohe KGV, die niedrige OpMargin und der Spender-Malus. Trotz hoher Gewichtung auf FCF reicht die Marge nicht.

#### 5. Fazit

Das Modell bevorzugt im aktuellen Zyklus Unternehmen mit hoher operativer Marge, starkem Wachstum und günstiger Bewertung, sofern sie Empfänger des CapEx sind. Es bestraft teure Spender mit schwacher Profitabilität. Die Logik ist darauf ausgelegt bis Q4 2027 stabil zu bleiben.# Ranking-
Ranking 
