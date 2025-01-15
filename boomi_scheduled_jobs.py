import streamlit as st
import pandas as pd
import requests

def color_enabled(val):
    color = 'green' if val=='true' else 'yellow' if val==False else 'red'
    return f'background-color: {color}'


def clear_cache():
    st.cache_data.clear()

@st.cache_data
def getJobs(atomId, label):
    r = requests.get('https://api.qa.trellis.arizona.edu/ws/rest/v1/util/getScheduledJobs/' + atomId) 

    st.text(label)
    
    if len(r.content) > 5:
        # Create a database session object that points to the URL.
        df = pd.DataFrame.from_dict(r.json())
        st.dataframe(data=df.style.applymap(color_enabled, subset=['enabled']), column_order=('Name','enabled','id','hours','minutes','daysOfWeek','daysOfMonth','months','years','cron'), use_container_width=True, height=None)

    else:
        st.text('No jobs scheduled')

    return

st.sidebar.title('Boomi - Scheduled Jobs')
st.sidebar.button('prod-trellis-molecule', on_click=getJobs, type="primary", args=['3d78acc2-9f2b-41ff-bbfd-a3f2ed30c89e', 'Prod Molecule'])
st.sidebar.button('nonprod-qa-atom', on_click=getJobs, type="primary", args=['58e8640c-7dcd-44fc-8308-a1f0239fc789', 'QA Atom'])
st.sidebar.button('sandbox-atom', on_click=getJobs, type="primary", args=['4e7219c4-fb66-40b5-ab23-0a5c9a32b5b1', 'Sandbox Atom'])
st.sidebar.button('Clear Cache', on_click=clear_cache)

