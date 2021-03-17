import numpy as np
import pandas as pd
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
import plotly.express as px


coordinates = {'Boden': (65.833333, 21.666667),
               'Borås': (57.7210839, 12.9407407),
               'Eskilstuna': (59.3717379, 16.5051474),
               'Falun': (60.6070068, 15.6323059),
               'Gävle': (60.6750132, 17.1467019),
               'Göteborg': (57.7072326, 11.9670171),
               'Halmstad': (56.6739826, 12.8574827),
               'Haparanda': (65.833333, 24.1),
               'Helsingborg': (56.0441984, 12.7040684),
               'Hudiksvall': (61.7281607, 17.105575),
               'Jönköping': (57.7825634, 14.165719),
               'Kalmar': (57.02784235, 16.575243899947836),
               'Karlskrona': (56.1621073, 15.5866422),
               'Karlstad': (59.3809146, 13.5027631),
               'Kiruna': (67.8550724, 20.2255482),
               'Kristianstad': (56.0293778, 14.1566859),
               'Lidköping': (58.5037196, 13.1576427),
               'Linköping': (58.4098135, 15.6245252),
               'Luleå': (65.5831187, 22.1459535),
               'Malmö': (55.6052931, 13.0001566),
               'Motala': (58.5420395, 15.041261),
               'Norrköping': (58.5909124, 16.1903511),
               'Nyköping': (58.7545409, 17.0120656),
               'Sandviken': (60.619422, 16.7724214),
               'Skellefteå': (64.7520185, 20.959339),
               'Skövde': (58.3898453, 13.8443792),
               'Stockholm': (59.3251172, 18.0710935),
               'Sundsvall': (62.3907552, 17.3071024),
               'Trelleborg': (55.37592, 13.1461522),
               'Uddevalla': (58.3490555, 11.9382855),
               'Umeå': (63.8256568, 20.2630745),
               'Uppsala': (59.8586126, 17.6387436),
               'Varberg': (57.1057412, 12.2502949),
               'Vetlanda': (57.36554305, 15.167830505066155),
               'Vänersborg': (58.3811988, 12.3226877),
               'Västervik': (57.7594186, 16.6385035),
               'Västerås': (59.6110992, 16.5463679),
               'Växjö': (56.8787183, 14.8094385),
               'Örebro': (59.2747287, 15.2151181),
               'Örnsköldsvik': (63.2888613, 18.7160209),
               'Östersund': (63.1793655, 14.6357061)}


def add_edge_to_df(df_cities, df_edges, from_city, to_city):
    start_lon = df_cities[df_cities['City'] == from_city]['Longitude'].iloc[0]
    start_lat = df_cities[df_cities['City'] == from_city]['Latitude'].iloc[0]
    end_lon = df_cities[df_cities['City'] == to_city]['Longitude'].iloc[0]
    end_lat = df_cities[df_cities['City'] == to_city]['Latitude'].iloc[0]

    df_edges = df_edges.append({'start_lat': start_lat, 'start_lon': start_lon,
                               'end_lat': end_lat, 'end_lon': end_lon}, ignore_index=True)
    return df_edges


def show(sol, number_of_cities):

    df_cities = pd.DataFrame.from_dict(
        coordinates, orient='index', columns=["Latitude", "Longitude"])
    df_cities = df_cities.reset_index().rename(columns={'index': "City"})
    df_cities = df_cities.iloc[:number_of_cities]
    df_sol = df_sol = pd.DataFrame(sol)

    df_edges = pd.DataFrame(
        columns=['start_lat', 'start_lon', 'end_lat', 'end_lon'])
    for index, row in df_sol.iterrows():

        df_edges = add_edge_to_df(df_cities, df_edges, row['From'], row['To'])

    max_flow = max(df_sol['Flow'])

    fig = go.Figure()

    for i in range(len(df_edges)):

        if df_sol.iloc[i]['Type'] != 'CORE':
            continue
        flow = df_sol.iloc[i]['Flow']
        hover_data = df_sol['From'][i] + ' - ' + \
            df_sol['To'] + ': ' + str(round(flow, 2))

        fig.add_trace(
            go.Scattermapbox(

                lon=[df_edges['start_lon'][i], df_edges['end_lon'][i]],
                lat=[df_edges['start_lat'][i], df_edges['end_lat'][i]],
                hoverinfo='text',
                text=hover_data,
                mode='markers+lines',
                line=dict(width=3, color='red'),
                opacity=0.7
            )
        )

    for i in range(len(df_edges)):
        if df_sol.iloc[i]['Type'] != 'SUB':
            continue
        flow = df_sol.iloc[i]['Flow']
        hover_data = df_sol['From'][i] + ' - ' + \
            df_sol['To'] + ': ' + str(round(flow, 2))
        fig.add_trace(
            go.Scattermapbox(

                lon=[df_edges['start_lon'][i], df_edges['end_lon'][i]],
                lat=[df_edges['start_lat'][i], df_edges['end_lat'][i]],
                hoverinfo='text',
                text=hover_data,
                mode='markers+lines',
                line=dict(width=1.5, color='blue'),
                opacity=0.7
            )
        )

    fig.add_trace(go.Scattermapbox(

        lon=df_cities['Longitude'],
        lat=df_cities['Latitude'],
        hoverinfo='text',
        text=df_cities['City'],
        mode='markers',
        marker=dict(
            size=4,
            color='rgb(255, 0, 0)',


        )))

    fig.update_layout(
        title_text='Automax',
        margin={'l': 0, 't': 0, 'b': 0, 'r': 0},
        mapbox={
            'center': {'lon': 10, 'lat': 10},
            'style': "carto-positron",
            'center': {'lon': -20, 'lat': -20},
            'zoom': 1},
        autosize=False,
        width=1000,
        height=1000,
        showlegend=False,)

    fig.show()
