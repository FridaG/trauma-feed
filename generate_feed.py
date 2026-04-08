import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
import os
import time
import json

# ============================================================
# CONFIGURATION
# ============================================================

# How many days back to search PubMed. Change this to adjust the lookback window.
# Recommended: 28 days (covers indexing delays and biweekly review cycles)
LOOKBACK_DAYS = 28

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
# Each entry is a tuple: (regex_pattern, display_label, parent_topic)
# Display labels use Australian English spelling
TRAUMA_KEYWORD_DEFS = [
    # General trauma
    (r"\btrauma\b", "trauma", "General Trauma"),
    (r"\bpolytrauma\b", "polytrauma", "General Trauma"),
    (r"\btraumatic\b", "traumatic", "General Trauma"),
    (r"\bmajor trauma\b", "major trauma", "General Trauma"),
    (r"\bblunt trauma\b", "blunt trauma", "General Trauma"),
    (r"\bpenetrating trauma\b", "penetrating trauma", "Penetrating"),
    (r"\binjury severity\b", "injury severity", "Systems/QI"),
    (r"\btrauma cent(er|re)\b", "trauma centre", "Systems/QI"),

    # Thoracic
    (r"\bha?emothorax\b", "haemothorax", "Thoracic"),
    (r"\bpneumothorax\b", "pneumothorax", "Thoracic"),
    (r"\brib fracture", "rib fracture", "Thoracic"),
    (r"\bflail chest\b", "flail chest", "Thoracic"),
    (r"\bthoracostomy\b", "thoracostomy", "Thoracic"),
    (r"\bthoracotomy\b", "thoracotomy", "Thoracic"),
    (r"\bchest drain\b", "chest drain", "Thoracic"),
    (r"\bintercostal catheter\b", "intercostal catheter", "Thoracic"),
    (r"\bcardiac tamponade\b", "cardiac tamponade", "Thoracic"),

    # Abdominal
    (r"\bsplenic (injury|laceration|rupture)\b", "splenic injury", "Abdominal"),
    (r"\bliver laceration\b", "liver laceration", "Abdominal"),
    (r"\bhepatic trauma\b", "hepatic trauma", "Abdominal"),
    (r"\bsolid organ injury\b", "solid organ injury", "Abdominal"),
    (r"\bdiaphragmatic injury\b", "diaphragmatic injury", "Abdominal"),
    (r"\bblunt abdominal\b", "blunt abdominal", "Abdominal"),

    # Pelvic
    (r"\bpelvic fracture\b", "pelvic fracture", "Pelvic"),
    (r"\bpelvic binder\b", "pelvic binder", "Pelvic"),
    (r"\bpelvic ring\b", "pelvic ring", "Pelvic"),
    (r"\bpelvic emboli[sz]ation\b", "pelvic embolisation", "Pelvic"),
    (r"\bpreperitoneal packing\b", "preperitoneal packing", "Pelvic"),
    (r"\bangioembol[iz]ation\b", "angioembolisation", "Pelvic"),

    # Haemorrhage & Resuscitation
    (r"\bREBOA\b", "REBOA", "Haemorrhage"),
    (r"\bha?emorrhagic shock\b", "haemorrhagic shock", "Haemorrhage"),
    (r"\bmassive transfusion\b", "massive transfusion", "Haemorrhage"),
    (r"\bmassive ha?emorrhage\b", "massive haemorrhage", "Haemorrhage"),
    (r"\bdamage control\b", "damage control", "Haemorrhage"),
    (r"\btranexamic acid\b", "tranexamic acid", "Haemorrhage"),
    (r"\bwhole blood resuscitation\b", "whole blood resuscitation", "Haemorrhage"),
    (r"\bpermissive hypotension\b", "permissive hypotension", "Haemorrhage"),
    (r"\bhypotensive resuscitation\b", "hypotensive resuscitation", "Haemorrhage"),
    (r"\btrauma.induced coagulopathy\b", "trauma-induced coagulopathy", "Haemorrhage"),
    (r"\bacute traumatic coagulopathy\b", "acute traumatic coagulopathy", "Haemorrhage"),
    (r"\bthromboelastography\b", "thromboelastography", "Haemorrhage"),
    (r"\bROTEM\b", "ROTEM", "Haemorrhage"),
    (r"\blethal triad\b", "lethal triad", "Haemorrhage"),
    (r"\bprothrombin complex\b", "prothrombin complex", "Haemorrhage"),
    (r"\bblood product", "blood product", "Haemorrhage"),
    (r"\bblood transfusion\b", "blood transfusion", "Haemorrhage"),
    (r"\bpacked red (blood )?cells?\b", "packed red blood cells", "Haemorrhage"),
    (r"\bprehospital blood\b", "prehospital blood", "Haemorrhage"),
    (r"\bfibrinogen\b", "fibrinogen", "Haemorrhage"),
    (r"\bcryoprecipitate\b", "cryoprecipitate", "Haemorrhage"),
    (r"\banticoagulant reversal\b", "anticoagulant reversal", "Haemorrhage"),

    # TBI
    (r"\btraumatic brain injur", "traumatic brain injury", "TBI"),
    (r"\bhead injur", "head injury", "TBI"),
    (r"\bintracranial ha?emorrhage\b", "intracranial haemorrhage", "TBI"),
    (r"\bsubdural ha?ematoma\b", "subdural haematoma", "TBI"),
    (r"\bepidural ha?ematoma\b", "epidural haematoma", "TBI"),
    (r"\bdiffuse axonal\b", "diffuse axonal injury", "TBI"),
    (r"\bdecompressive craniectomy\b", "decompressive craniectomy", "TBI"),
    (r"\bICP monitoring\b", "ICP monitoring", "TBI"),
    (r"\bintracranial pressure monitoring\b", "intracranial pressure monitoring", "TBI"),
    (r"\bconcussion\b", "concussion", "TBI"),

    # Spine
    (r"\bspinal cord injury\b", "spinal cord injury", "Spine"),
    (r"\bspinal injury\b", "spinal injury", "Spine"),
    (r"\bspinal fracture\b", "spinal fracture", "Spine"),
    (r"\bcervical spine (injury|trauma|clearance)\b", "cervical spine", "Spine"),
    (r"\bspinal immobili[sz]ation\b", "spinal immobilisation", "Spine"),
    (r"\bc-spine\b", "c-spine", "Spine"),
    (r"\bspinal clearance\b", "spinal clearance", "Spine"),

    # Penetrating
    (r"\bgunshot wound", "gunshot wound", "Penetrating"),
    (r"\bstab wound", "stab wound", "Penetrating"),
    (r"\bpenetrating injur", "penetrating injury", "Penetrating"),
    (r"\bblast injur", "blast injury", "Penetrating"),

    # Burns
    (r"\bburn injur", "burn injury", "Burns"),
    (r"\bthermal injury\b", "thermal injury", "Burns"),

    # Paediatric
    (r"\bpa?ediatric trauma\b", "paediatric trauma", "Paediatric"),

    # Obstetric
    (r"\btrauma in pregnancy\b", "trauma in pregnancy", "Obstetric"),
    (r"\bmaternal trauma\b", "maternal trauma", "Obstetric"),
    (r"\bresuscitative hysterotomy\b", "resuscitative hysterotomy", "Obstetric"),
    (r"\bperimortem c(ae)?sarean\b", "perimortem caesarean", "Obstetric"),

    # Orthopaedic
    (r"\bopen fracture", "open fracture", "Orthopaedic"),
    (r"\bortho?pa?edic trauma\b", "orthopaedic trauma", "Orthopaedic"),
    (r"\bfemur fracture\b", "femur fracture", "Orthopaedic"),
    (r"\bfemoral fracture\b", "femoral fracture", "Orthopaedic"),
    (r"\btibial fracture\b", "tibial fracture", "Orthopaedic"),
    (r"\bhumeral fracture\b", "humeral fracture", "Orthopaedic"),
    (r"\blong bone fracture\b", "long bone fracture", "Orthopaedic"),
    (r"\bcompartment syndrome\b", "compartment syndrome", "Orthopaedic"),
    (r"\brhabdomyolysis\b", "rhabdomyolysis", "Orthopaedic"),
    (r"\bfat embolism\b", "fat embolism", "Orthopaedic"),

    # Facial/Neck
    (r"\bfacial fracture\b", "facial fracture", "Facial/Neck"),
    (r"\bmaxillofacial trauma\b", "maxillofacial trauma", "Facial/Neck"),
    (r"\bLe Fort\b", "Le Fort", "Facial/Neck"),
    (r"\bmandib(le|ular) fracture\b", "mandibular fracture", "Facial/Neck"),
    (r"\borbital fracture\b", "orbital fracture", "Facial/Neck"),
    (r"\bglobe rupture\b", "globe rupture", "Facial/Neck"),
    (r"\bneck injur", "neck injury", "Facial/Neck"),
    (r"\blaryngeal injury\b", "laryngeal injury", "Facial/Neck"),
    (r"\btracheal injury\b", "tracheal injury", "Facial/Neck"),

    # Vascular
    (r"\bvascular injury\b", "vascular injury", "Vascular"),
    (r"\baortic (injury|transection)\b", "aortic injury", "Vascular"),
    (r"\bjunctional ha?emorrhage\b", "junctional haemorrhage", "Vascular"),

    # Imaging
    (r"\bFAST (exam|ultrasound)\b", "FAST exam", "Imaging"),
    (r"\beFAST\b", "eFAST", "Imaging"),
    (r"\bfocused assessment with sonography\b", "focused assessment with sonography", "Imaging"),
    (r"\btrauma ultrasound\b", "trauma ultrasound", "Imaging"),
    (r"\bPOCUS\b", "POCUS", "Imaging"),
    (r"\bwhole body CT\b", "whole body CT", "Imaging"),
    (r"\btrauma CT\b", "trauma CT", "Imaging"),

    # Procedures
    (r"\bcricothyr(otomy|oidotomy)\b", "cricothyroidotomy", "Procedures"),
    (r"\bsurgical airway\b", "surgical airway", "Procedures"),
    (r"\bemergency laparotomy\b", "emergency laparotomy", "Procedures"),
    (r"\bopen abdomen\b", "open abdomen", "Procedures"),
    (r"\btemporary abdominal closure\b", "temporary abdominal closure", "Procedures"),
    (r"\btourniquet\b", "tourniquet", "Procedures"),

    # Prehospital & Retrieval
    (r"\btrauma resuscitation\b", "trauma resuscitation", "Prehospital"),
    (r"\btrauma team\b", "trauma team", "Prehospital"),
    (r"\btrauma activation\b", "trauma activation", "Prehospital"),
    (r"\bprehospital trauma\b", "prehospital trauma", "Prehospital"),
    (r"\bhelicopter emergency\b", "helicopter emergency", "Prehospital"),
    (r"\baeromedical\b", "aeromedical", "Prehospital"),
    (r"\btrauma retrieval\b", "trauma retrieval", "Prehospital"),
    (r"\bretrieval medicine\b", "retrieval medicine", "Prehospital"),
    (r"\bHEMS\b", "HEMS", "Prehospital"),
    (r"\bprehospital\b", "prehospital", "Prehospital"),

    # Systems/QI
    (r"\binjury prevention\b", "injury prevention", "Systems/QI"),
    (r"\btrauma mortality\b", "trauma mortality", "Systems/QI"),
    (r"\bpreventable death\b", "preventable death", "Systems/QI"),
    (r"\btrauma registry\b", "trauma registry", "Systems/QI"),
    (r"\btrauma quality\b", "trauma quality", "Systems/QI"),
    (r"\bATLS\b", "ATLS", "Systems/QI"),
    (r"\bEMST\b", "EMST", "Systems/QI"),

    # Cardiac Arrest (Traumatic)
    (r"\btraumatic cardiac arrest\b", "traumatic cardiac arrest", "Cardiac Arrest"),
    (r"\btrauma arrest\b", "trauma arrest", "Cardiac Arrest"),
    (r"\btraumatic amputation\b", "traumatic amputation", "Cardiac Arrest"),
    (r"\bcrush (injury|syndrome)\b", "crush injury", "Cardiac Arrest"),
    (r"\bECMO\b", "ECMO", "Cardiac Arrest"),
    (r"\bECPR\b", "ECPR", "Cardiac Arrest"),

    # Other
    (r"\bnon.?accidental injury\b", "non-accidental injury", "Paediatric"),
    (r"\bcode crimson\b", "code crimson", "Haemorrhage"),
    (r"\bdrowning\b", "drowning", "General Trauma"),
    (r"\bmultiple organ (dysfunction|failure)\b", "multiple organ dysfunction", "General Trauma"),
    (r"\bMODS\b", "MODS", "General Trauma"),
]

# Build compiled patterns and lookup structures
TRAUMA_PATTERNS = [(re.compile(pat, re.IGNORECASE), label, topic)
                   for pat, label, topic in TRAUMA_KEYWORD_DEFS]

# All possible parent topics (used by the web interface to show all chips)
ALL_TOPICS = sorted(set(topic for _, _, topic in TRAUMA_KEYWORD_DEFS))

EXCLUDE_PUB_TYPES = {
    "Comment", "Letter", "Editorial", "Erratum",
    "Published Erratum", "Retraction of Publication",
    "Expression of Concern",
}

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


def search_pubmed(journal_name, issn, days_back=LOOKBACK_DAYS):
    """Search PubMed for recent articles from a specific journal by ISSN and name."""
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    date_to = datetime.now().strftime("%Y/%m/%d")

    # Search by both ISSN and journal name to catch articles indexed either way
    params = {
        "db": "pubmed",
        "term": f'("{issn}"[ISSN] OR "{journal_name}"[Journal])',
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
    batch_size = 50

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

                # Extract structured abstract with section labels
                abstract_parts = article_elem.findall(".//AbstractText")
                abstract_sections = []
                for part in abstract_parts:
                    label = part.get("Label")
                    text = part.text or ""
                    if label:
                        abstract_sections.append(f"**{label}**: {text}")
                    else:
                        abstract_sections.append(text)
                abstract = "\n\n".join(abstract_sections)

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


def match_trauma_keywords(article):
    """Return matched keyword labels and parent topics for an article."""
    text = f"{article['title']} {article['abstract']}"
    matched_labels = []
    matched_topics = set()
    for pattern, label, topic in TRAUMA_PATTERNS:
        if pattern.search(text):
            if label not in matched_labels:
                matched_labels.append(label)
            matched_topics.add(topic)
    return matched_labels, sorted(matched_topics)


def is_trauma_relevant(article):
    """Check if an article matches any trauma keyword."""
    text = f"{article['title']} {article['abstract']}"
    for pattern, _, _ in TRAUMA_PATTERNS:
        if pattern.search(text):
            return True
    return False


def is_excluded_pub_type(article):
    """Check if article is a comment, letter, editorial, etc."""
    if article["pub_types"] & EXCLUDE_PUB_TYPES:
        return True
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

        # Format abstract for RSS: convert **Label**: to bold HTML
        abstract_html = article["abstract"]
        abstract_html = re.sub(
            r'\*\*([^*]+)\*\*:',
            r'<b>\1</b>:',
            abstract_html
        )
        abstract_html = abstract_html.replace("\n\n", "<br/><br/>")

        desc = f"<b>{article['journal']}</b><br/>"
        desc += f"{authors_str}<br/><br/>"
        if abstract_html:
            desc += abstract_html
        else:
            desc += "No abstract available."

        if article.get("doi"):
            desc += f'<br/><br/><a href="https://doi.org/{article["doi"]}">Full text via DOI</a>'

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


def generate_json(articles, output_path="docs/articles.json"):
    """Generate a JSON file with all article data for the Cloudflare Worker."""

    tier1_issns = set(TIER1_JOURNALS.values())

    json_articles = []
    for article in articles:
        matched_labels, matched_topics = match_trauma_keywords(article)

        # For Tier 1 articles with no keyword matches, tag as "General Trauma"
        if not matched_topics and article["issn"] in tier1_issns:
            matched_topics = ["General Trauma"]

        json_articles.append({
            "pmid": article["pmid"],
            "title": article["title"],
            "abstract": article["abstract"],
            "journal": article["journal"],
            "authors": article["authors"],
            "date": article["date_str"],
            "doi": article["doi"],
            "tier": "core" if article["issn"] in tier1_issns else "filtered",
            "topics": matched_topics,
            "matched_keywords": matched_labels,
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/",
        })

    output = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "total_articles": len(json_articles),
        "all_topics": ALL_TOPICS,
        "articles": json_articles,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"JSON written to {output_path} with {len(json_articles)} articles")


# ============================================================
# MAIN
# ============================================================

def main():
    all_articles = []
    all_journals = {**TIER1_JOURNALS, **TIER2_JOURNALS}
    tier1_issns = set(TIER1_JOURNALS.values())

    print(f"Searching {len(all_journals)} journals (last {LOOKBACK_DAYS} days)...")
    print(f"Rate limiting: {REQUEST_DELAY}s between requests")
    print(f"API key: {'Yes' if API_KEY else 'No'}")
    print()

    for name, issn in all_journals.items():
        print(f"  Searching: {name} ({issn})...")
        try:
            pmids = search_pubmed(name, issn)
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
    generate_json(unique_articles)


if __name__ == "__main__":
    main()
