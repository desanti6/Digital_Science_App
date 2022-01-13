import pandas as pd
import seaborn as sns
import streamlit as st
import plotly as pl
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
from pycountry_convert import country_alpha2_to_country_name, country_name_to_country_alpha3
from PIL import Image

st.set_page_config(page_title=None, page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)
sns.set_theme(palette="dark")

# Pull in data
# df = pd.read_csv(r"query.csv")
df = pd.read_json(r"json_query.json", lines=True)
df.rename(columns={"name_1": "Publisher", "title":"Journal Name"}, inplace=True)
# print(df.columns)
# print(df.isnull().sum()) # Check for nulls... some in the state codes
# print(df.describe()) # Review

# Change date to datetime type
df['date'] = pd.to_datetime(df['date'])
df['month'] = pd.DatetimeIndex(df['date']).month
# Convert country code from 2 to 3 letter iso-3166-3 for use in plotly
df['country_code'] = df.country_code.apply(lambda x: country_name_to_country_alpha3(country_alpha2_to_country_name(x)))
# print(df.dtypes) # Check datatypes

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
gdf_bar.plot(kind="bar", ax=ax, rot=45, label="")
ax.axhline(y=gdf_bar.describe()["50%"], c='r', alpha=0.5, linestyle="-.", label="mean")
ax.set_ylabel("Number of Publications")
ax.set_xlabel("Publication Date")
x_ticks = ax.get_xticks()
for i,j in enumerate(x_ticks):
    ax.annotate(gdf_bar[i],(j,gdf_bar[i]), size=10, ha="center")
ax.get_yaxis().set_ticks([])
ax.annotate("mean="+str(gdf_bar.describe()["50%"]),(.05, gdf_bar.describe()["50%"]*1.05), fontsize=6, c='r')
ax.legend()

# Create a organization breakdown for each research org
gdf_orgs = df.groupby(["name","latitude","longitude","country_code","country"]).agg({"pubid":'count',"score":'max',"times_cited":"sum"}).sort_values(by="pubid",ascending=False).reset_index()
gdf_orgs.rename(columns={"pubid":"Publications","times_cited":"Times Cited","score":"Altmetrics Score"}, inplace=True)
# gdf_orgs.head()

# Combine and goup the data by country
gdf_country = df.groupby(["country_code","country"]).agg({"pubid":'count',"score":'max',"times_cited":"sum"}).sort_values(by="pubid",ascending=False).reset_index()
gdf_country.rename(columns={"pubid":"Publications","times_cited":"Times Cited","score":"Altmetrics Score"}, inplace=True)

#####################
# Dash Board
#####################

st.title("COVID-19 Research Analysis")
st.write("The COVID-19 pandemic has garnered a significant amount of attention around the world. The virus has distrupted the world, \
    with death tolls in the millions. Naturally, the scientific community has responded by conducting extensive research on\
        the virus. Thousands of peer-reviewed journal articles over the last two years have been written and published during\
        the pandemic. The two figures below give a sense of scope for the amount of research conducted by accounting for the number \
            of publications related to COVID-19 in the last two year. The data in this analysis reports the top 10,000 publications from \
                a dataset about COVID-19 publications (see link at bottom of page for reference).")
col1, col2 = st.columns(2)
with col1:
    st.subheader("COVID-19 Related Publications")
    st.pyplot(fig_line)

with col2:
    st.subheader("COVID-19 Publications by Month")
    st.pyplot(fig_bar)
    st.write("Publications tend to be released in conjunction with other works.\
    For brevity, books and presentations were not included in this data, as they\
        tend to be reflected by the number of publications on a given topic.")

with st.expander("",expanded=True):
    st.header("COVID-19 Research Organizations with Publications related to vaccines")

    st.markdown("The response to the COVID-19 pandemic has resulted in the production of vaccines against the virus. \
        Various research organizations have conducted vaccine research. The following data lists the top research \
            organization that have published a journal article about vaccines. Vaccinations continue to be an important \
            area of research, as varients have been continuing to develop and spread the disease.")
    
    # Vaccine Dataframe development
    st.subheader("Select a sorting metric")
    st.write("These organizations have specifically published regarding vaccinations. They may have \
        also published on other COVID-19 topics.")
    selection_vac = st.selectbox("",
    ["Publications","Altmetrics Score","Times Cited"], key="select0")

    df_vaccine = df[(df['preferred'].str.contains("vaccine",na=False))|
    (df['preferred'].str.contains("vaccination",na=False))|
    (df['preferred'].str.contains("antibody"))]
  
    gdf_vaccine = df_vaccine.groupby(by="name").agg({"pubid":"count","score":"max","times_cited":"mean"})
    gdf_vaccine = gdf_vaccine.rename(columns={"pubid":"Publications", "score":"Altmetrics Score", "times_cited":"Times Cited"})
    gdf_vaccine = gdf_vaccine.sort_values(selection_vac,ascending=False)[['Publications',"Altmetrics Score", "Times Cited"]]
    st.dataframe(gdf_vaccine.style.format({"Publications":"{:.0f}", "Altmetrics Score":"{:.1f}","Times Cited":"{:.0f}"}))
    
    ## JOIN GDF VACCINE WTIH DF LAT AND LON ON NAME
    gdf_vac_map = pd.merge(left=gdf_vaccine.reset_index(), right=df_vaccine, how="inner",left_on="name", right_on="name")
    gdf_vac_map = gdf_vac_map[["name","Publications","Altmetrics Score","Times Cited", "latitude","longitude","country"]]
    gdf_vac_map = gdf_vac_map.drop_duplicates().reset_index().drop("index",axis=1)

    if selection_vac == "Publications":
        st.write("Publications shows the number of publications from a country in the given dataset")
    elif selection_vac == "Altmetrics Score":
        st.write(f"{selection_vac} shows the highest {selection_vac} from the dataset for each country")
        st.write("More information about Altmetrics can be found at https://www.digital-science.com/product/altmetric/")
    else:
        st.write(f"{selection_vac} shows the sum of {selection_vac} from the dataset for each country")

    subset_vac = gdf_vac_map[['name','latitude','longitude','country',selection_vac]]
    # Location plot of where vaccine work is being done
    mapfig_vacs = px.scatter_geo(subset_vac,
                    lat='latitude', lon='longitude',hover_name="name",
                    color='country', size=selection_vac)
    mapfig_vacs.update_layout(height=800,width=600)
    # mapfig_vacs.show()
    st.plotly_chart(mapfig_vacs,use_container_width=True)

    st.markdown("As varients continue to spread, it is important to note the location of where they are first\
        developing. Most of the varients have seemingly developed in warm, tropical regions around or south of the\
            equator. Geospatial analysis of where vaccines have been deployed may find these areas highly undervaccinated\
                and further research in these locations could provide researchers with a jump start on identifying \
                    varients early.")
    st.image(Image.open('NYT Image.png'), caption="Data on varients from https://www.nytimes.com/interactive/2021/health/coronavirus-variant-tracker.html")

    st.write("The most prominent vaccine research organizations are generally located in first world countries and are mainly \
        well known universities. The first three research organizations conducting vaccine research (when sorted by publications)\
            are the University of Oxford, Imperial College London, and Harvard University, all three of which have well known \
                medical schools. The rankings of most prominent research organization change slightly when utilizing the other metrics\
                available but many of these other organizations have had limited chances to publish and probably do not have the \
                    extensive staff and research capabilities of major medical hospitals. While it is somewhat of a self-fulfilling \
                    prophecy to suggest, continued funding to universities with medical schools will likely yield excellent advances\
                        in vaccine research.")

st.write("The following sections can be expanded and examined to identify research organizations\
    by geographic location at a national scale or based actual location.")

# Research orgs map
with st.expander("COVID-19 Research Organizations Ranked for Countries ranked by Optional Metrics",expanded=False):
    st.header("")
    st.subheader("Select a metric to examine")
    selection = st.selectbox("",
    ["Publications","Altmetrics Score","Times Cited"], key="select1")
    
    if selection == "Publications":
        st.write("Publications shows the number of publications from a country in the given dataset")
    elif selection == "Altmetrics Score":
        st.write(f"{selection} shows the highest {selection} from the dataset for each country")
        st.write("More information about Altmetrics can be found at https://www.digital-science.com/product/altmetric/")
    else:
        st.write(f"{selection} shows the sum of {selection} from the dataset for each country")

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
with st.expander("COVID-19 Research Ranked for Countries ranked by Optional Metrics",expanded=False):
    
# Map of which countries are doing research into COVID 19
    st.header("")
    st.subheader("Select a metric to examine")
    
    selection = st.selectbox("",
    ["Publications","Altmetrics Score","Times Cited"], key="select2")
    values = gdf_country[selection]

    if selection == "Publications":
        st.write("Publications shows the number of publications from a country in the given dataset")
    elif selection == "Altmetrics Score":
        st.write(f"{selection} shows the highest {selection} from the dataset for each country")
        st.write("More information about Altmetrics can be found at https://www.digital-science.com/product/altmetric/")
    else:
        st.write(f"{selection} shows the sum of {selection} from the dataset for each country")
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

st.markdown("COVID-19 Publication data: https://console.cloud.google.com/marketplace/product/digitalscience-public/covid-19-dataset-dimensions?project=elite-caster-300319")
