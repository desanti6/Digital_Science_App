import pandas as pd
import seaborn as sns
import streamlit as st
import plotly as pl
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
from pycountry_convert import country_alpha2_to_country_name, country_name_to_country_alpha3
st.set_page_config(page_title=None, page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)
sns.set_theme(palette="dark")

# Pull in data
# df = pd.read_csv(r"query.csv")
df = pd.read_json(r"json_query.json", lines=True)
df.rename(columns={"name_1": "Publisher", "title":"Journal Name"}, inplace=True)
# print(df.columns)
print(df.isnull().sum()) # Check for nulls... some in the state codes
print(df.describe()) # Review

# Change date to datetime type
df['date'] = pd.to_datetime(df['date'])
df['month'] = pd.DatetimeIndex(df['date']).month
# Convert country code from 2 to 3 letter iso-3166-3 for use in plotly
df['country_code'] = df.country_code.apply(lambda x: country_name_to_country_alpha3(country_alpha2_to_country_name(x)))
print(df.dtypes) # Check datatypes

# Publication Line Plot
gdf_line = df.groupby(by="date").count() # Group by time
gdf_area=gdf_line['pubid'].cumsum()
gdf_area=gdf_area.to_frame().rename(columns={'pubid':"Publications"})

# Plot the publication could by date
fig_line, ax = plt.subplots(figsize=(6,3))
# ax.plot(gdf_line.index,gdf_line.year, "r-o", alpha=0.5)
ax.fill_between(gdf_area.index,gdf_area.Publications,  alpha=0.5)
ax.set_ylabel('Cumulative number of\n publications related to COVID-19')
plt.xticks(rotation=45)

# Plot a bar plot with the number of publications per month
gdf_bar = df.set_index('date').groupby(pd.Grouper(freq="M")).size()
gdf_bar.index = gdf_bar.index.map(lambda s: s.strftime('%Y-%m'))

fig_bar, ax = plt.subplots(figsize=(8,3))
gdf_bar.plot(kind="bar", ax=ax, rot=45)
ax.set_ylabel("Number of Publications")
ax.set_xlabel("Publication Date")
x_ticks = ax.get_xticks()
for i,j in enumerate(x_ticks):
    ax.annotate(gdf_bar[i],(j,gdf_bar[i]), size=10, ha="center")
ax.get_yaxis().set_ticks([])

# Create a organization breakdown for each research org
gdf_orgs = df.groupby(["name","latitude","longitude","country_code","country"]).agg({"pubid":'count',"score":'max',"times_cited":"max","recent_citations":"max"}).sort_values(by="pubid",ascending=False).reset_index()
gdf_orgs.rename(columns={"pubid":"Publications","times_cited":"Times Cited","score":"Altmetrics Score","recent_citations":"Recent Citations"}, inplace=True)
# gdf_orgs.head()

# Combine and goup the data by country
gdf_country = df.groupby(["country_code","country"]).agg({"pubid":'count',"score":'max',"times_cited":"max","recent_citations":"max"}).sort_values(by="pubid",ascending=False).reset_index()
gdf_country.rename(columns={"pubid":"Publications","times_cited":"Times Cited","score":"Altmetrics Score","recent_citations":"Recent Citations"}, inplace=True)

#####################
# Dash Board
#####################

st.title("COVID-19 Research analysis")

col1, col2 = st.columns(2)
with col1:
    st.subheader("COVID-19 Related Publications")
    st.pyplot(fig_line)
st.write("This includes any publications related to the COVID-19 pandemic")

with col2:
    st.subheader("COVID-19 Research Organizations with Publications related to vaccines")
    st.write("By comparison, these organizations have specifically published regarding vaccinations. They may have \
        also published on other COVID-19 topics.")
    gdf_vaccine = df[(df['preferred'].str.contains("vaccine",na=False))|
    (df['preferred'].str.contains("vaccination",na=False))|
    (df['preferred'].str.contains("antibody"))].groupby(by="name").agg({"pubid":"count","score":"median"})
    gdf_vaccine = gdf_vaccine.rename(columns={"pubid":"Publications", "score":"Altmetrics Score"})
    gdf_vaccine = gdf_vaccine.sort_values("Altmetrics Score",ascending=False)[['Publications',"Altmetrics Score"]]
    st.dataframe(gdf_vaccine.style.format({"Publications":"{:.0f}", "Altmetrics Score":"{:.1f}"}))


st.subheader("COVID-19 Publications by Month")
st.pyplot(fig_bar)
st.write("Publications tend to be released in conjunction with other works.\
    For brevity, books and presentations were not included in this data, as they\
        tend to be reflected by the number of publications on a given topic.")


# Research orgs map
with st.expander("",expanded=True):
    st.header("COVID-19 Research Organizations")
    st.subheader("Select a metric to examine")
    selection = st.selectbox("",
    ["Publications","Altmetrics Score","Times Cited","Recent Citations"], key="select1")
    
    if selection == "Publications":
        st.write("Publications shows the number of publications from a country in the given dataset")
    elif selection == "Altmetrics Score":
        st.write(f"{selection} shows the highest {selection} from the dataset for each country")
        st.write("More information about Altmetrics can be found at https://www.digital-science.com/product/altmetric/")
    else:
        st.write(f"{selection} shows the maximum {selection} from the dataset for each country")

    subset = gdf_orgs[['name','latitude','longitude','country',selection]]
    # Location plot of where work is being done
    mapfig_orgs = px.scatter_geo(subset,
                    lat='latitude', lon='longitude',hover_name="name",
                    color='country',size=selection)
    mapfig_orgs.update_layout(height=800,width=600)
    # mapfig_orgs.show()
    st.plotly_chart(mapfig_orgs,use_container_width=True)
    check1 = st.checkbox("Show dataframe?", key="orgs_key")
    if check1:
        st.write(subset)

# Metrics by country map
with st.expander("",expanded=True):
    
# Map of which countries are doing research into COVID 19
    st.header("COVID-19 Research Metrics")
    st.subheader("Select a metric to examine")
    
    selection = st.selectbox("",
    ["Publications","Altmetrics Score","Times Cited","Recent Citations"], key="select2")
    values = gdf_country[selection]

    if selection == "Publications":
        st.write("Publications shows the number of publications from a country in the given dataset")
    elif selection == "Altmetrics Score":
        st.write(f"{selection} shows the highest {selection} from the dataset for each country")
        st.write("More information about Altmetrics can be found at https://www.digital-science.com/product/altmetric/")
    else:
        st.write(f"{selection} shows the maximum {selection} from the dataset for each country")
 # Plotly commands   
    mapfig_country = go.Figure(data=go.Choropleth(
    locations=gdf_country['country_code'],
    z = values,
    text=gdf_country["country"],
    colorscale="viridis",
    autocolorscale=True,
    reversescale=False,
    marker_line_color='darkgray',
    marker_line_width=0.5,
    colorbar_tickprefix = '',
    colorbar_title = selection
    ))

    mapfig_country.update_layout(
    title_text='COVID-19 '+selection+ ' by Country',
    height=600,
    geo=dict(
        showframe=False,
        showcoastlines=True,
        projection_type='equirectangular'
    ),
     annotations = [dict(
        x=0.01,
        y=0.01,
        xref='paper',
        yref='paper',
        text='Source: https://console.cloud.google.com/marketplace/product/digitalscience-public/covid-19-dataset-dimensions?project=elite-caster-300319',
        showarrow = False)]
    )
    # Plotly Call   
    st.plotly_chart(mapfig_country,use_container_width=True)
    check2 = st.checkbox("Show dataframe?")
    if check2:
        st.write(gdf_country.sort_values(by=selection, ascending=False))


