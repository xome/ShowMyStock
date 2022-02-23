import os

import requests
import time
import datetime
import json
import csv
import pandas
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import lines
from matplotlib.axis import YAxis

INTRADAY: str = "Intraday"
MONAT: str = "Monat"
JAHR: str = "Jahr"
SEIT_KAUF: str = "seit Kauf"


def male_verlaeufe(start: int, ende: int, name_datei: str):
    df = pandas.read_csv(filepath_or_buffer="E:/Dev/Projekte/ShowMyStock/isins.csv", delimiter=";", header=0)
    print(df)
    verlaeufe: dict = {}
    sum_aktuelle_werte = 0
    sum_einkaufswerte = 0
    for row in df.iterrows():
        print("---------------------------------------------------------------")
        aktie = row[1]
        s = requests.Session()
        print(aktie)
        isin = aktie[3]
        sum_einkaufswerte = sum_einkaufswerte + aktie['STK'] * aktie['Kaufpreis']
        params = {"resolution": "M",
                  "isKeepResolutionForLatestWeeksIfPossible": False,
                  "from": start,
                  "to": ende,
                  "isBidAskPrice": False,
                  "symbols": "XFRA:{}".format(isin)
                  }
        url = "https://api.boerse-frankfurt.de/v1/tradingview/lightweight/history"
        r = s.get(url=url, params=params, stream=True)
        count_health_events = 0
        history: dict = {}
        verlauf: list = []
        try:
            for line in r.iter_lines():
                string: str = line.decode('UTF-8')
                data: dict = {}
                if 'health' in string:
                    count_health_events = count_health_events + 1
                if string.startswith('data:{'):
                    data = json.loads(string[5:])
                    if 'quotes' in data.keys():
                        verlauf = data['quotes']['timeValuePairs']
                        pairs: list = []
                        for timeValuePair in verlauf:
                            pairs.append(
                                [datetime.datetime.fromtimestamp(timeValuePair['time']), timeValuePair['value']])
                        verlaeufe[aktie['Wertpapier']] = pandas.DataFrame(pairs, columns=['Zeit', 'Wert'])
                    elif 'quoteUpdate' in data.keys():
                        aktie['Aktueller Wert'] = data['quoteUpdate']['value']
                        break
                if count_health_events >= 2:
                    verlauf.reverse()
                    aktie['Aktueller Wert'] = verlauf[0]['value']
                    break
        except Exception:
            print("Fehler bei Anfrage. Weiter.")
        finally:
            r.close()
        if 'Aktueller Wert' in aktie and aktie['Aktueller Wert'] is not None:
            aktueller_wert = aktie['Aktueller Wert']
        else:
            if aktie['Wertpapier'] in verlaeufe:
                verlauf: pandas.DataFrame = verlaeufe[aktie['Wertpapier']]
                aktueller_wert = verlauf.value.iat[-1]
            else:
                aktueller_wert = aktie['Kaufpreis']
        df.loc[df.ISIN == isin, 'Aktueller Wert'] = aktueller_wert
        sum_aktuelle_werte = sum_aktuelle_werte + aktueller_wert * aktie['STK']
    print(df)
    matplotlib.rcParams['text.color'] = 'white'
    matplotlib.rcParams['axes.labelcolor'] = 'white'
    matplotlib.rcParams['xtick.color'] = 'white'
    matplotlib.rcParams['ytick.color'] = 'white'
    px = 1 / plt.rcParams['figure.dpi']
    fig_gesamt, ax_gesamt = plt.subplots(nrows=3, ncols=5, figsize=(1900 * px, 600 * px))
    y_koord = 1
    x_koord = 0
    for (name, verlauf) in verlaeufe.items():
        print("---------------------------------------------------------------")
        print("Verarbeitung für {}".format(name))
        # print(verlauf)
        einkaufswert = 0.0
        aktueller_wert = 0.0
        stk = 1
        # WTF, Python? Der Idx ist manchmal 0 und manchmal 1?????????
        for val in df.loc[df.Wertpapier == name, 'Kaufpreis']:
            einkaufswert = val
        for val in df.loc[df.Wertpapier == name, 'Aktueller Wert']:
            aktueller_wert = val
        for val in df.loc[df.Wertpapier == name, 'STK']:
            stk = val

        gewinn = round((aktueller_wert - einkaufswert) * stk, 2)
        x = verlauf['Zeit']
        y = verlauf['Wert']
        ax_gesamt[y_koord, x_koord].plot(x, y, color="white")
        ax_gesamt[y_koord, x_koord].set_facecolor('black')
        ax_gesamt[y_koord, x_koord].set(xlabel='Zeit', ylabel='Preis',
                                        title="{} ({})".format(name, '%.2f' % gewinn))

        if name_datei == INTRADAY:
            ax_gesamt[y_koord, x_koord].xaxis.set_major_locator(mdates.HourLocator(interval=1))
            ax_gesamt[y_koord, x_koord].xaxis.set_major_formatter(mdates.DateFormatter('%H'))
        elif name_datei == MONAT:
            ax_gesamt[y_koord, x_koord].xaxis.set_major_locator(mdates.DayLocator(interval=3))
            ax_gesamt[y_koord, x_koord].xaxis.set_major_formatter(mdates.DateFormatter('%d'))
        elif name_datei == JAHR:
            ax_gesamt[y_koord, x_koord].xaxis.set_major_locator(mdates.DayLocator(interval=28))
            ax_gesamt[y_koord, x_koord].xaxis.set_major_formatter(mdates.DateFormatter('%U'))
        elif name_datei == SEIT_KAUF:
            ax_gesamt[y_koord, x_koord].xaxis.set_major_locator(mdates.DayLocator(interval=7))
            ax_gesamt[y_koord, x_koord].xaxis.set_major_formatter(mdates.DateFormatter('%U'))

        axes = ax_gesamt[y_koord, x_koord].axes
        extra_y_ticks: list = [einkaufswert, aktueller_wert]
        extra_y_ticks.sort()

        # axes.set_yticks(list(axes.get_yticks()) + extra_y_ticks)

        line = lines.Line2D(xdata=x, ydata=[einkaufswert])
        line.set_color('gray')
        ax_gesamt[y_koord, x_koord].add_line(line)

        # fig_gesamt[x_koord, y_koord].autofmt_xdate()
        # fig_gesamt[x_koord, y_koord].set_facecolor('black')
        if y_koord < 2:
            y_koord = y_koord + 1
        else:
            y_koord = 0
            x_koord = x_koord + 1
    ax_gesamt[0, 0].set_facecolor('black')
    ax_gesamt[0, 0].set_xticks([])
    ax_gesamt[0, 0].set_yticks([])
    ax_gesamt[0, 0].set_title('Überblick Depot %s' % name_datei)
    text_kwargs = dict(ha='center', va='center', fontsize=13, color='white', fontname='DejaVu Sans Mono')
    gewinn = round(sum_aktuelle_werte - sum_einkaufswerte, 2)
    gewinn_in_prozent = round(gewinn / sum_einkaufswerte * 100, 2)
    text = "Stand       {} Uhr\n" \
           "Einkaufswert  : {}€\n" \
           "aktueller Wert: {}€\n" \
           "Gewinn:    {:,}€ ({:,}%)".format(
        datetime.datetime.now().strftime("%H:%M:%S"),
        round(sum_einkaufswerte, 2), round(sum_aktuelle_werte, 2), gewinn, gewinn_in_prozent)
    ax_gesamt[0, 0].text(0.5, 0.5, text, text_kwargs)

    kosten = -298.95 - 17.85 - 5.9
    dividenden = 45.15 + 71.2 + 100 + 5 + 20
    text_zusatzkosten_und_dividenden = "Kosten: {:,}€ ({:,}%)\n " \
                                       "Zinsen: {:,}€ ({:,}%)\n " \
                                       "Gewinn: {:,}€".format(
        kosten, round(kosten * 100 / sum_aktuelle_werte, 2), dividenden,
        round(dividenden * 100 / sum_aktuelle_werte, 2), round(gewinn + kosten + dividenden, 2))
    ax_gesamt[2, 4].set_facecolor('black')
    ax_gesamt[2, 4].set_xticks([])
    ax_gesamt[2, 4].set_yticks([])
    ax_gesamt[2, 4].text(0.5, 0.5, text_zusatzkosten_und_dividenden, text_kwargs)
    ax_gesamt[1, 4].set_facecolor('black')
    ax_gesamt[1, 4].set_xticks([])
    ax_gesamt[1, 4].set_yticks([])
    # ax_gesamt[0, 4].set_facecolor('black')
    # ax_gesamt[0, 4].set_xticks([])
    # ax_gesamt[0, 4].set_yticks([])

    fig_gesamt.autofmt_xdate()
    fig_gesamt.set_facecolor('black')
    plt.tight_layout()
    dateipfad = "E:/Dev/Projekte/ShowMyStock/image/plot_%s.png" % name_datei
    if os.path.isfile(dateipfad):
        os.remove(dateipfad)

    fig_gesamt.savefig(dateipfad)

    print("Aktueller Wert - Einkauf = Gewinn: {} - {} = {}".format(round(sum_aktuelle_werte, 2),
                                                                   round(sum_einkaufswerte, 2), gewinn))


if __name__ == '__main__':
    now = round(time.time())
    now_datetime = datetime.datetime.now()
    start = round(now - now_datetime.hour * 60 * 60 - now_datetime.minute * 60 - now_datetime.second)
    male_verlaeufe(start=start, ende=now, name_datei=INTRADAY)

    start = round(now - 60 * 60 * 24 * 30)
    male_verlaeufe(start=start, ende=now, name_datei=MONAT)

    start = round(now - 60 * 60 * 24 * 365)
    male_verlaeufe(start=start, ende=now, name_datei=JAHR)

    start = 1617227999  # 31.03.2021 23:59:59 Uhr
    male_verlaeufe(start=start, ende=now, name_datei=SEIT_KAUF)

    exit(0)
