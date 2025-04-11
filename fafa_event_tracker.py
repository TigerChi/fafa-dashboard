
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
from dash import dash_table

# 讀取資料
df = pd.read_csv("fafa_data.csv", parse_dates=["開始時間"])
df['時間（小時）'] = df['開始時間'].dt.hour + df['開始時間'].dt.minute / 60
df['日期'] = df['開始時間'].dt.date

# App 初始化
app = Dash(__name__)

event_options = [{'label': etype, 'value': etype} for etype in sorted(df['項目'].unique())]
chart_modes = [
    {'label': '原始事件點圖', 'value': 'scatter'},
    {'label': '每日癲癇次數（含標記）', 'value': 'bar_count'},
    {'label': '每日癲癇總秒數（含標記）', 'value': 'bar_duration'}
]

app.layout = html.Div([
    html.H2("發發事件互動視覺化工具（可點擊長條顯示詳情）"),
    html.Label("選擇日期區間"),
    dcc.DatePickerRange(
        id='date-range',
        min_date_allowed=df['開始時間'].min().date(),
        max_date_allowed=df['開始時間'].max().date(),
        start_date=df['開始時間'].min().date(),
        end_date=df['開始時間'].max().date()
    ),
    html.Br(),
    html.Label("選擇要顯示的項目"),
    dcc.Dropdown(
        id='event-filter',
        options=event_options,
        value=['癲癇', '起床', '癲癇用藥', '其他用藥'],
        multi=True
    ),
    html.Label("圖表模式"),
    dcc.Dropdown(
        id='chart-mode',
        options=chart_modes,
        value='bar_count',
        clearable=False
    ),
    dcc.Graph(id='event-graph'),
    html.H4(id='detail-title'),
    dash_table.DataTable(
        id='detail-table',
        columns=[
            {'name': '開始時間', 'id': '開始時間'},
            {'name': '記錄值（秒）', 'id': '記錄值'},
            {'name': '描述', 'id': '描述'}
        ],
        data=[],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={'fontWeight': 'bold'},
    )
])

@app.callback(
    Output('event-graph', 'figure'),
    Input('event-filter', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input('chart-mode', 'value')
)
def update_graph(selected_events, start_date, end_date, chart_mode):
    dff = df[df['項目'].isin(selected_events)]
    dff = dff[(dff['開始時間'].dt.date >= pd.to_datetime(start_date).date()) &
              (dff['開始時間'].dt.date <= pd.to_datetime(end_date).date())]

    if chart_mode == 'scatter':
        fig = px.scatter(
            dff,
            x='時間（小時）',
            y='日期',
            color='項目',
            hover_data=['項目', '記錄值', '描述', '開始時間'],
            title="事件散點圖",
            height=800
        )
        fig.update_yaxes(type='category', autorange="reversed")
        fig.update_layout(legend_title_text='項目')
        return fig

    elif chart_mode in ['bar_count', 'bar_duration']:
        epilepsy_df = df[df['項目'] == '癲癇']
        epilepsy_df = epilepsy_df[
            (epilepsy_df['開始時間'].dt.date >= pd.to_datetime(start_date).date()) &
            (epilepsy_df['開始時間'].dt.date <= pd.to_datetime(end_date).date())
        ]

        if chart_mode == 'bar_count':
            agg_df = epilepsy_df.groupby(epilepsy_df['開始時間'].dt.date).size().reset_index(name='癲癇次數')
            y_label = '癲癇次數'
            title = '每日癲癇次數（含 S101 與藥量調整標記）'
        else:
            epilepsy_df['記錄值'] = pd.to_numeric(epilepsy_df['記錄值'], errors='coerce')
            agg_df = epilepsy_df.groupby(epilepsy_df['開始時間'].dt.date)['記錄值'].sum().reset_index(name='總秒數')
            y_label = '總秒數'
            title = '每日癲癇總秒數（含 S101 與藥量調整標記）'

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=agg_df['開始時間'],
            y=agg_df[y_label],
            name='癲癇',
            marker_color='indianred'
        ))

        for label, symbol, color in [('S101', 'circle', 'blue'), ('藥量調整', 'diamond', 'green')]:
            mark_df = df[df['項目'] == label]
            mark_df = mark_df[
                (mark_df['開始時間'].dt.date >= pd.to_datetime(start_date).date()) &
                (mark_df['開始時間'].dt.date <= pd.to_datetime(end_date).date())
            ]
            fig.add_trace(go.Scatter(
                x=mark_df['開始時間'].dt.date,
                y=[0]*len(mark_df),
                mode='markers',
                name=label,
                marker=dict(symbol=symbol, size=12, color=color),
                hovertext=mark_df['描述']
            ))

        fig.update_layout(
            title=title,
            xaxis_title='日期',
            yaxis_title=y_label,
            height=700
        )
        return fig

@app.callback(
    Output('detail-title', 'children'),
    Output('detail-table', 'data'),
    Input('event-graph', 'clickData'),
    State('chart-mode', 'value')
)
def display_click_details(clickData, chart_mode):
    if chart_mode not in ['bar_count', 'bar_duration'] or clickData is None:
        return "", []

    clicked_date = clickData['points'][0]['x']
    clicked_date = pd.to_datetime(clicked_date).date()
    selected_day = df[(df['項目'] == '癲癇') & (df['開始時間'].dt.date == clicked_date)]
    selected_day = selected_day.sort_values('開始時間')

    table_data = selected_day[['開始時間', '記錄值', '描述']].copy()
    table_data['開始時間'] = table_data['開始時間'].astype(str)
    return f"{clicked_date} 癲癇詳細記錄", table_data.to_dict('records')

if __name__ == "__main__":
    app.run(debug=True)
