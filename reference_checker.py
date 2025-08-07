import re
import requests
import streamlit as st

# Replace with your Brave Search API key
BRAVE_API_KEY = "BSAdFSWbTy9rrwETkphzDIXvCPi4-jR"

def extract_doi(reference):
    match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", reference)
    return match.group(1) if match else None

def search_crossref_by_doi(doi):
    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()["message"]
    except Exception:
        pass
    return None

def search_crossref_by_title(title):
    url = "https://api.crossref.org/works"
    params = {"query.title": title, "rows": 3}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()["message"]["items"]
    except Exception:
        pass
    return []

def brave_search(query):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": 3
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("web", {}).get("results", [])
    except Exception:
        pass
    return []

def normalize(text):
    return re.sub(r"[\s:;,.!?()\[\]\"']", "", text.lower())

def check_reference(reference):
    doi = extract_doi(reference)
    if doi:
        cr_result = search_crossref_by_doi(doi)
        if not cr_result:
            return "🟥", "DOI not found in CrossRef."
        crossref_title = cr_result.get("title", [""])[0]
        if normalize(crossref_title) in normalize(reference):
            return "🟩", "DOI found and title matches."
        else:
            return "🟧", f"DOI found, but title differs. CrossRef title: '{crossref_title}'"
    else:
        cr_items = search_crossref_by_title(reference)
        for item in cr_items:
            crossref_title = item.get("title", [""])[0]
            if normalize(crossref_title) in normalize(reference):
                return "🟩", "Found in CrossRef by title match."
        brave_results = brave_search(reference)
        if brave_results:
            result = brave_results[0]
            return "🟧", f"Not found in CrossRef. Found via Brave: {result.get('title', 'Untitled')} - {result.get('url')}"
        return "🟥", "Reference not found."

def main():
    st.title("📚 Reference Checker")
    st.write("Paste references below, one per line. This will check each for validity using CrossRef and Brave Search as backup.")
    input_text = st.text_area("Enter references:", height=300)

    if st.button("Check References"):
        references = input_text.strip().split("\n")
        results = []
        for ref in references:
            if ref.strip():
                status, message = check_reference(ref.strip())
                results.append((ref.strip(), status, message))

        st.subheader("Results")
        for ref, status, message in results:
            st.markdown(f"**{status}** {ref}")
            st.caption(message)

if __name__ == "__main__":
    main()
