import re
import requests
import streamlit as st
from fuzzywuzzy import fuzz

BRAVE_API_KEY = "BSAdFSWbTy9rrwETkphzDIXvCPi4-jR"

def extract_doi(reference):
    match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", reference)
    return match.group(1) if match else None

def search_crossref_by_doi(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()["message"]
    except Exception:
        pass
    return None

def search_crossref_by_title(title):
    try:
        url = "https://api.crossref.org/works"
        params = {"query.title": title, "rows": 5}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()["message"]["items"]
    except Exception:
        pass
    return []

def brave_search(query):
    try:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"X-Subscription-Token": BRAVE_API_KEY}
        params = {"q": query, "count": 5}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("web", {}).get("results", [])
    except Exception:
        pass
    return []

def remove_year(text):
    return re.sub(r"\b(19|20)\d{2}\b", "", text)

def parse_reference(reference):
    author_match = re.match(r"^(.*?)[\(\.]", reference)
    author = author_match.group(1).strip() if author_match else ""
    temp = reference
    if author:
        temp = temp.replace(author, "")
    temp = remove_year(temp)
    title = temp.strip(" .,-")
    if not title:
        title = reference.replace(author, "").strip()
    return author, title

def fuzzy_match(str1, str2):
    return fuzz.token_set_ratio(str1.lower(), str2.lower())

def extract_surnames(author_str):
    if not author_str:
        return ""
    parts = re.split(r"[,&]| and ", author_str)
    surnames = []
    for p in parts:
        p = p.strip()
        if p:
            surname = p.split()[-1]
            surnames.append(surname.lower())
    return " ".join(surnames)

def check_reference(reference):
    doi = extract_doi(reference)
    ref_author, ref_title = parse_reference(reference)
    ref_surnames = extract_surnames(ref_author)

    # CrossRef checking
    if doi:
        cr_result = search_crossref_by_doi(doi)
        if cr_result:
            cr_title = cr_result.get("title", [""])[0]
            cr_authors = cr_result.get("author", [])
            cr_author_names = " ".join([a.get('family','') for a in cr_authors if 'family' in a]).lower()

            title_score = fuzzy_match(ref_title, cr_title)
            author_score = fuzzy_match(ref_surnames, cr_author_names)

            if title_score > 85 and author_score > 70:
                return "🟩", "DOI found and both title and author surname match CrossRef."
            elif title_score > 85 or author_score > 70:
                crossref_status, crossref_msg = "🟧", "DOI found but author surname or title differs from CrossRef."
            else:
                crossref_status, crossref_msg = "🟥", "DOI found but neither title nor author surname match CrossRef."
        else:
            crossref_status, crossref_msg = "🟥", "DOI found but not found in CrossRef."
    else:
        crossref_status, crossref_msg = "🟥", "Reference not found in CrossRef."
        cr_items = search_crossref_by_title(ref_title)
        for item in cr_items:
            cr_title = item.get("title", [""])[0]
            cr_authors = item.get("author", [])
            cr_author_names = " ".join([a.get('family','') for a in cr_authors if 'family' in a]).lower()

            title_score = fuzzy_match(ref_title, cr_title)
            author_score = fuzzy_match(ref_surnames, cr_author_names)

            if title_score > 85 and author_score > 70:
                return "🟩", "Found match in CrossRef by title and author surname."
            elif title_score > 85:
                crossref_status, crossref_msg = "🟧", "Found match in CrossRef by title only."

    # If CrossRef is amber or red, try Brave search
    if crossref_status != "🟩":
        brave_results = brave_search(reference)
        for result in brave_results:
            brave_title = result.get("title", "")
            brave_snippet = result.get("description", "")
            brave_url = result.get("url", "")

            brave_snippet_surnames = extract_surnames(brave_snippet)

            title_score = fuzzy_match(ref_title, brave_title)
            author_score = fuzzy_match(ref_surnames, brave_snippet_surnames)

            if title_score > 85 and author_score > 65:
                return "🟩", f"Brave search: matched title and author surname. Source: [{brave_title}]({brave_url})"
            elif title_score > 85 and author_score < 30:
                # Title matches but author surnames differ a lot — treat as amber but warn user
                if crossref_status == "🟥":
                    crossref_status, crossref_msg = "🟧", (
                        f"Brave search: title similar but author surnames differ significantly. Source: [{brave_title}]({brave_url})"
                    )

    return crossref_status, crossref_msg

def main():
    st.title("📚 Reference Checker with CrossRef and Brave Search")

    input_text = st.text_area("Enter references here:", height=300)

    if st.button("Check References"):
        if not input_text.strip():
            st.warning("Please enter at least one reference.")
            return
        refs = [r.strip() for r in input_text.strip().split("\n") if r.strip()]
        results = []
        for ref in refs:
            try:
                status, msg = check_reference(ref)
                results.append((ref, status, msg))
            except Exception as e:
                results.append((ref, "🟥", f"Error checking reference: {e}"))

        st.subheader("Results")
        for ref, status, msg in results:
            st.markdown(f"**{status}** {ref}")
            st.caption(msg)

if __name__ == "__main__":
    main()
