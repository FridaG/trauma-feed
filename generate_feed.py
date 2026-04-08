import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
import os
import time

# ============================================================
# CONFIGURATION
# ============================================================

# Tier 1: Core trauma journals — ALL articles included
TIER1_JOURNALS = {
    "Injury": "0020-1383",
    "Eur J Trauma Emerg Surg": "1863-9941",
    "J Trauma Acute Care Surg": "2163-0763",
    "Scand J Trauma Resusc Emerg Med": "1757-7241",
    "Trauma Surg Acute Care Open": "2397-5776",
    "World J Emerg Surg": "1749-7922",
}

# Tier 2: High-impact journals — only trauma-relevant articles
TIER2_JOURNALS = {
    "N Engl J Med": "1533-4406",
    "JAMA": "1538-3598",
    "Lancet": "1474-547X",
    "BMJ": "1756-1833",
    "Resuscitation": "1873-1570",
    "Ann Emerg Med": "1097-6760",
    "Emerg Med J": "1472-0213",
    "Emerg Med Australas": "1742-6723",
    "Acad Emerg Med": "1553-2712",
    "Am J Emerg Med": "1532-8171",
    "Crit Care Med": "1530-0293",
    "Intensive Care Med": "1432-1238",
    "Crit Care": "1466-609X",
    "Ann Surg": "1528-1140",
    "Br J Surg": "1365-2168",
    "JAMA Surg": "2168-6262",
    "J Neurosurg": "1933-0693",
    "Neurosurgery": "1524-4040",
    "Prehosp Emerg Care": "1545-0066",
    "J Am Coll Surg": "1879-1190",
    "Cochrane Database Syst Rev": "1469-493X",
}

# Trauma keywords for filtering Tier 2 articles
TRAUMA_KEYWORDS = [
    r"\btrauma\b", r"\bpolytrauma\b", r"\btraumatic\b",
    r"\bmajor trauma\b", r"\bblunt trauma\b", r"\bpenetrating trauma\b",
    r"\binjury severity\b", r"\btrauma cent(er|re)\b",
    r"\bha?emothorax\b", r"\bpneumothorax\b", r"\brib fracture",
    r"\bflail chest\b", r"\bthoracostomy\b", r"\bthoracotomy\b",
    r"\bchest drain\b", r"\bintercostal catheter\b",
    r"\bcardiac tamponade\b",
    r"\bsplenic (injury|laceration|rupture)\b",
    r"\bliver laceration\b", r"\bhepatic trauma\b",
    r"\bsolid organ injury\b", r"\bdiaphragmatic injury\b",
    r"\bblunt abdominal\b",
    r"\bpelvic fracture\b", r"\bpelvic binder\b", r"\bpelvic ring\b",
    r"\bpelvic emboli[sz]ation\b", r"\bpreperitoneal packing\b",
    r"\bangioembol[iz]ation\b",
    r"\bREBOA\b", r"\bha?emorrhagic shock\b",
    r"\bmassive transfusion\b", r"\bmassive ha?emorrhage\b",
    r"\bdamage control\b", r"\btranexamic acid\b",
    r"\bwhole blood resuscitation\b", r"\bpermissive hypotension\b",
    r"\bhypotensive resuscitation\b",
    r"\btrauma.induced coagulopathy\b", r"\bacute traumatic coagulopathy\b",
    r"\bthromboelastography\b", r"\bROTEM\b",
    r"\blethal triad\b", r"\bprothrombin complex\b",
    r"\btraumatic brain injur", r"\bhead injur",
    r"\bintracranial ha?emorrhage\b", r"\bsubdural ha?ematoma\b",
    r"\bepidural ha?ematoma\b", r"\bdiffuse axonal\b",
    r"\bdecompressive craniectomy\b", r"\bICP monitoring\b",
    r"\bintracranial pressure monitoring\b",
    r"\bspinal cord injury\b", r"\bspinal injury\b", r"\bspinal fracture\b",
    r"\bcervical spine (injury|trauma|clearance)\b",
    r"\bspinal immobili[sz]ation\b", r"\bc-spine\b", r"\bspinal clearance\b",
    r"\bgunshot wound", r"\bstab wound", r"\bpenetrating injur",
    r"\bblast injur", r"\bburn injur", r"\bthermal injury\b",
    r"\bpa?ediatric trauma\b", r"\btrauma in pregnancy\b",
    r"\bmaternal trauma\b", r"\bgeriatric trauma\b", r"\belderly trauma\b",
    r"\bopen fracture", r"\bortho?pa?edic trauma\b",
    r"\bfemur fracture\b", r"\bfemoral fracture\b",
    r"\btibial fracture\b", r"\bhumeral fracture\b",
    r"\blong bone fracture\b", r"\bcompartment syndrome\b",
    r"\brhabdomyolysis\b", r"\bfat embolism\b",
    r"\bfacial fracture\b", r"\bmaxillofacial trauma\b",
    r"\bLe Fort\b", r"\bmandib(le|ular) fracture\b",
    r"\borbital fracture\b", r"\bglobe rupture\b",
    r"\bneck injur", r"\blaryngeal injury\b", r"\btracheal injury\b",
    r"\bvascular injury\b", r"\baortic (injury|transection)\b",
    r"\bjunctional ha?emorrhage\b",
    r"\bFAST (exam|ultrasound)\b", r"\beFAST\b",
    r"\bfocused assessment with sonography\b",
    r"\btrauma ultrasound\b", r"\bPOCUS\b",
    r"\bwhole body CT\b", r"\btrauma CT\b",
    r"\bcricothyr(otomy|oidotomy)\b", r"\bsurgical airway\b",
    r"\bemergency laparotomy\b", r"\bopen abdomen\b",
    r"\btemporary abdominal closure\b",
    r"\bresuscitative hysterotomy\b", r"\bperimortem c(ae)?sarean\b",
    r"\btrauma resuscitation\b", r"\btrauma team\b", r"\btrauma activation\b",
    r"\bprehospital trauma\b", r"\bhelicopter emergency\b",
    r"\baeromedical retrieval\b", r"\btrauma retrieval\b",
    r"\binjury prevention\b", r"\btrauma mortality\b",
    r"\bpreventable death\b", r"\btrauma registry\b", r"\btrauma quality\b",
    r"\bATLS\b", r"\bEMST\b",
    r"\btraumatic cardiac arrest\b", r"\btrauma arrest\b",
    r"\btraumatic amputation\b", r"\bcrush (injury|syndrome)\b",
    r"\bnon.?accidental injury\b", r"\bcode crimson\b",
    r"\bdrowning\b", r"\bECMO\b", r"\bECPR\b",
    r"\bmultiple organ (dysfunction|failure)\b", r"\bMODS\b",
    r"\banticoagulant reversal\b",
]

TRAUMA_PATTERNS = [re.compile(kw, re.IGNORECASE) for kw in TRAUMA_KEYWORDS]

EXCLUDE_PUB_TYPES = {
    "Comment", "Letter", "Editorial", "Erratum",
    "Published Erratum", "Retraction of Publication",
    "Expression of Concern",
}

LOOKBACK_DAYS = 14

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EMAIL = os.environ.get("NCBI_EMAIL", "your.email@example.com")
API_KEY = os.environ.get("NCBI_API_KEY", "")

# Rate limiting: NCBI allows 3/sec without key, 10/sec with key
REQUEST_DELAY = 0.15 if API_KEY else 0.4

# ============================================================
# FUNCTIONS
# ============================================================

def api_get(url, params):
    """Make a rate-limited GET request to the NCBI API."""
    if API_KEY:
        params["api_key"] = API_KEY
    params["email"] = EMAIL

    time.sleep(REQUEST_DELAY)
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r


def search_pubmed(issn, days_back=LOOKBACK_DAYS):
    """Search PubMed for recent articles from a specific journal by ISSN."""
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    date_to = datetime.now().strftime("%Y/%m/%d")

    params = {
        "db": "pubmed",
        "term": f'"{issn}"[ISSN]',
        "datetype": "edat",
        "mindate": date_from,
        "maxdate": date_to,
        "retmax": 200,
        "retmode": "json",
    }

    r = api_get(f"{NCBI_BASE}/esearch.fcgi", params)
    data = r.json()
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_details(pmids):
    """Fetch article details for a list of PMIDs, in batches to avoid 414 errors."""
    if not pmids:
        return []

    all_articles = []
    batch_size = 50  # Fetch 50 at a time to keep URLs short

    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
        }

        r = api_get(f"{NCBI_BASE}/efetch.fcgi", params)
        root = ET.fromstring(r.content)

        for article_elem in root.findall(".//PubmedArticle"):
            try:
                pmid = article_elem.findtext(".//PMID")
                title = article_elem.findtext(".//ArticleTitle") or "No title"
                abstract_parts = article_elem.findall(".//AbstractText")
                abstract = " ".join(
                    (part.text or "") for part in abstract_parts
                )

                pub_types = set()
                for pt in article_elem.findall(".//PublicationType"):
                    if pt.text:
                        pub_types.add(pt.text)

                journal = article_elem.findtext(".//Journal/ISOAbbreviation") or ""
                issn_elem = article_elem.find(".//Journal/ISSN")
                issn = issn_elem.text if issn_elem is not None else ""

                pub_date_elem = article_elem.find(".//PubDate")
                if pub_date_elem is not None:
                    year = pub_date_elem.findtext("Year") or "2026"
                    month = pub_date_elem.findtext("Month") or "Jan"
                    day = pub_date_elem.findtext("Day") or "1"
                    date_str = f"{year} {month} {day}"
                else:
                    date_str = "2026 Jan 1"

                authors = []
                for author in article_elem.findall(".//Author"):
                    last = author.findtext("LastName") or ""
                    initials = author.findtext("Initials") or ""
                    if last:
                        authors.append(f"{last} {initials}".strip())

                doi = ""
                for aid in article_elem.findall(".//ArticleId"):
                    if aid.get("IdType") == "doi":
                        doi = aid.text or ""

                all_articles.append({
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                    "journal": journal,
                    "issn": issn,
                    "pub_types": pub_types,
                    "date_str": date_str,
                    "authors": authors,
                    "doi": doi,
                })
            except Exception as e:
                print(f"  Warning: Error parsing article: {e}")
                continue

    return all_articles


def is_trauma_relevant(article):
    """Check if an article matches trauma keywords in title or abstract."""
    text = f"{article['title']} {article['abstract']}"
    for pattern in TRAUMA_PATTERNS:
        if pattern.search(text):
            return True
    return False


def is_excluded_pub_type(article):
    """Check if article is a comment, letter, editorial, etc."""
    if article["pub_types"] & EXCLUDE_PUB_TYPES:
        return True
    # Also check title for common patterns (catches unindexed ahead-of-print)
    title_lower = article["title"].lower()
    exclude_phrases = ["comment on", "reply to", "erratum", "retraction",
                       "expression of concern", "correction to"]
    return any(phrase in title_lower for phrase in exclude_phrases)


def generate_rss(articles, output_path="docs/feed.xml"):
    """Generate an RSS 2.0 XML feed from a list of articles."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "Trauma Literature Feed"
    ET.SubElement(channel, "description").text = (
        "Curated trauma medicine literature from key journals"
    )
    ET.SubElement(channel, "link").text = "https://pubmed.ncbi.nlm.nih.gov/"
    ET.SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    tier1_issns = set(TIER1_JOURNALS.values())

    for article in articles:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = article["title"]

        link = f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/"
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "guid").text = link

        authors_str = ", ".join(article["authors"][:3])
        if len(article["authors"]) > 3:
            authors_str += " et al."

        desc = f"<b>{article['journal']}</b><br/>"
        desc += f"{authors_str}<br/><br/>"
        if article["abstract"]:
            desc += article["abstract"][:500]
            if len(article["abstract"]) > 500:
                desc += "..."
        else:
            desc += "No abstract available."

        ET.SubElement(item, "description").text = desc
        ET.SubElement(item, "pubDate").text = article["date_str"]

        ET.SubElement(item, "category").text = article["journal"]
        if article["issn"] in tier1_issns:
            ET.SubElement(item, "category").text = "Tier 1 - Core Trauma"
        else:
            ET.SubElement(item, "category").text = "Tier 2 - Filtered"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="unicode", xml_declaration=True)
    print(f"Feed written to {output_path} with {len(articles)} articles")


# ============================================================
# MAIN
# ============================================================

def main():
    all_articles = []
    all_journals = {**TIER1_JOURNALS, **TIER2_JOURNALS}
    tier1_issns = set(TIER1_JOURNALS.values())

    print(f"Searching {len(all_journals)} journals...")
    print(f"Rate limiting: {REQUEST_DELAY}s between requests")
    print(f"API key: {'Yes' if API_KEY else 'No'}")
    print()

    for name, issn in all_journals.items():
        print(f"  Searching: {name} ({issn})...")
        try:
            pmids = search_pubmed(issn)
        except requests.exceptions.HTTPError as e:
            print(f"    ERROR searching {name}: {e}")
            print(f"    Waiting 5 seconds and continuing...")
            time.sleep(5)
            continue

        print(f"    Found {len(pmids)} articles")

        if pmids:
            try:
                articles = fetch_details(pmids)
            except requests.exceptions.HTTPError as e:
                print(f"    ERROR fetching details for {name}: {e}")
                print(f"    Waiting 5 seconds and continuing...")
                time.sleep(5)
                continue

            for article in articles:
                if is_excluded_pub_type(article):
                    continue

                if issn in tier1_issns:
                    all_articles.append(article)
                elif is_trauma_relevant(article):
                    all_articles.append(article)

    # Deduplicate by PMID
    seen = set()
    unique_articles = []
    for a in all_articles:
        if a["pmid"] not in seen:
            seen.add(a["pmid"])
            unique_articles.append(a)

    # Sort by PMID descending (roughly newest first)
    unique_articles.sort(key=lambda x: int(x["pmid"]), reverse=True)

    print(f"\nTotal articles after filtering: {len(unique_articles)}")
    generate_rss(unique_articles)


if __name__ == "__main__":
    main()
