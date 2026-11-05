"""Pre-built knowledge chunks from sparrowi.com for vector search."""

from backend.chunker import Chunk, _make_chunk_id

# These chunks are auto-ingested into Qdrant on startup so that
# company-related queries also match via semantic vector search.

WEBSITE_CHUNKS = [
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 0),
        text=(
            "Sparrow Interactive Pvt Ltd — Company Overview\n"
            "Website: www.sparrowi.com\n"
            "Sparrow Interactive is an experiential technology and phygital solutions company "
            "serving real estate, retail, corporate, healthcare, and education sectors. They create immersive phygital (physical + digital) "
            "experiences for developers, brands, and institutions, blending visualization technology, "
            "VR/AR, and interactive solutions. The company transforms how spaces and brands "
            "are experienced through cutting-edge technology and creative storytelling.\n\n"
            "Tagline: Creating Striking Visualisations of Tomorrow's Spaces | "
            "Building Immersive and Interactive Phygital experiences\n\n"
            "Key Stats:\n"
            "- 2,500+ projects executed across India and Middle East\n"
            "- 250+ esteemed developers, corporations and institutions as clients\n"
            "- 30+ years of industry pioneership (founded 1996)\n"
            "- 150+ digital evangelists on the team\n\n"
            "Social Media:\n"
            "- Facebook: facebook.com/Sparrow.Interactive\n"
            "- Instagram: @sparrowinteractive\n"
            "- LinkedIn: Sparrow Interactive Pvt Ltd"
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 1),
        text=(
            "Sparrow Interactive — Services: Experiential Journeys\n"
            "Turnkey phygital journeys through projects with immersive narratives. "
            "Sparrow Interactive crafts memorable walk-through journeys that emotionally connect "
            "buyers with properties. These journeys combine storytelling, spatial design, and "
            "technology to create unforgettable experiences in real estate showrooms and "
            "experience centers."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 2),
        text=(
            "Sparrow Interactive — Services: Immersive Experiences\n"
            "Medium to large-scale projection rooms using VR and AR technologies. "
            "Sparrow Interactive designs and builds immersive environments for real estate "
            "experience centers, combining visual, audio, and tactile elements to create "
            "powerful spatial experiences. They use projection mapping, AR/VR, and "
            "multi-sensory installations that bring architectural visions to life."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 3),
        text=(
            "Sparrow Interactive — Services: Architectural Visualization\n"
            "3D rendering and animated films with cinematic storytelling. "
            "High-quality 3D renders, CGI walkthroughs, and photorealistic visualizations "
            "of properties before they are built. Sparrow Interactive's architectural "
            "visualization team creates stunning visual content that helps buyers see and "
            "experience properties that are still under construction or in planning stages."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 4),
        text=(
            "Sparrow Interactive — Services: Scale Models\n"
            "Life-like, detailed scale representations of projects. "
            "Precision-crafted physical scale models of buildings and townships, combining "
            "traditional craftsmanship with modern technology. Sparrow Interactive creates "
            "detailed architectural scale models that give real estate buyers a tangible, "
            "three-dimensional understanding of projects."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 5),
        text=(
            "Sparrow Interactive — Services: Interactive Solutions\n"
            "Touch tables, touch walls, and interactive navigation systems. "
            "Sparrow Interactive develops custom interactive technology solutions including "
            "touch-screen kiosks, interactive displays, AR apps, and digital tools "
            "that engage buyers and streamline the real estate sales process."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 6),
        text=(
            "Sparrow Interactive — About Us & Company History\n"
            "Sparrow Interactive was founded in 1996 by co-directors Rashmi Kohli and Ashish Mahajan. "
            "With a team of 150+ digital evangelists, we sit at the intersection of technology, creativity and innovation. "
            "Brand philosophy: 'Amaze. Delight. Repeat.'\n\n"
            "Company Milestones:\n"
            "- 1996: Company founded, started with web designing\n"
            "- 2003: First step towards 3D Architectural Visualization\n"
            "- 2006: First Indian firm to introduce photorealism in architectural 3D\n"
            "- 2012: First to introduce locally produced, high-quality scale models in India\n"
            "- 2013: Leveled up experiential solutions through holographic imagery and multi-touch environments\n"
            "- 2018: Launched experience centres\n"
            "- 2026: Moving towards producing smarter models and systems; first three-sided ready-to-setup immersive experience\n\n"
            "The company operates across India and the Middle East, with 250+ developer/corporate clients."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com/about-us/",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 7),
        text=(
            "Sparrow Interactive — Office Locations & Contact Information\n"
            "Headquarters city: Noida (in the Delhi NCR region), Uttar Pradesh, India.\n"
            "Sparrow Interactive is headquartered in Noida — NOT in Gurgaon, Delhi, or any other city. "
            "Cities such as Gurgaon, Kolkata, Hyderabad, and Jamnagar appear only as client project locations, not as our office.\n"
            "Headquarters address:\n"
            "7th Floor, Plot No 19A, Filmcity, Sector 16A, Noida - 201301, Uttar Pradesh, India\n"
            "Google Maps: https://www.google.com/maps/place/Sparrow+Interactive+Pvt+Ltd/@28.5657419,77.3143025,17z/data=!3m1!4b1!4m6!3m5!1s0x390ce6b6a6b7752b:0xc6a3c9972fe96f41!8m2!3d28.5657372!4d77.3168774!16s%2Fg%2F1hm5t7ss_?entry=ttu&g_ep=EgoyMDI2MDIxMC4wIKXMDSoASAFQAw%3D%3D\n\n"
            "Contact:\n"
            "- India: biz@sparrowi.com | +91-9810119956\n"
            "- Middle East: biz@sparrowglobal.ae | +971-588515640 | +91-9902778888\n"
            "- Africa: biz@sparrowi.com | +91-8800098402\n"
            "- Careers / HR: hr@sparrowi.com\n\n"
            "Social Media:\n"
            "- Instagram: @sparrowinteractive\n"
            "- LinkedIn: Sparrow Interactive Pvt Ltd\n"
            "- Facebook: Sparrow.Interactive"
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com/contact-us/",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 8),
        text=(
            "Sparrow Interactive — Project Portfolio Highlights & Case Studies\n"
            "Sparrow Interactive has delivered 2,500+ projects across India and the Middle East "
            "for 250+ developers, corporations and institutions.\n\n"
            "Notable case studies:\n"
            "- M3M Capital, Sec 113 (Gurgaon) — Luxury residential EC with golf-style living, 23ft curved screen, projection-mapped model, apartment explorer pods\n"
            "- Emami Aastha, Joka (Kolkata) — Biophilic villa township EC with nature-led spatial journey\n"
            "- Gaurs Trecento (Noida) — Premium residential EC with 360-degree LED installation and projection-based model\n"
            "- Reliance Industries, Jamnagar — Industrial experience with sensor-based standees and LED floor-based model\n"
            "- Riverscape by Arete, Vapi — Community-led EC with fluid design and wellness-driven experience\n"
            "- Lansum Evana, Chevella (Hyderabad) — Site-integrated biophilic villa EC with glass pavilions\n"
            "- IndiaBulls Estate & Club Dhani (Gurgaon) — Club-inspired estate living EC\n\n"
            "Top clients include Reliance, Adani, Godrej, DLF, Brigade, IndiaBulls, EMAAR, Runwal, Sobha, Lodha."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com/blog/",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 14),
        text=(
            "Sparrow Interactive — Global Presence & International Operations\n"
            "Sparrow Interactive is a global brand operating across three major regions:\n\n"
            "1. **India (Headquarters — Noida)**\n"
            "   - Headquarters city: Noida (Delhi NCR), Uttar Pradesh\n"
            "   - Office: 7th Floor, Plot No 19A, Filmcity, Sector 16A, Noida - 201301, Uttar Pradesh\n"
            "   - Contact: biz@sparrowi.com | +91-9810119956\n"
            "   - Key clients include DLF, Ace Group, Gaurs Group, Runwal Group, and other leading real estate developers\n\n"
            "2. **Middle East (UAE & Oman)**\n"
            "   - Regional operations led by Tarrun Kumaria, Director of Middle East Operations\n"
            "   - Contact: biz@sparrowglobal.ae | +971-588515640 | +91-9902778888\n"
            "   - Active presence in UAE, Oman, and the wider Gulf region\n\n"
            "3. **Africa**\n"
            "   - Contact: biz@sparrowi.com | +91-8800098402\n"
            "   - Expanding operations in the African market\n\n"
            "With 200+ clients globally and projects delivered across India, the Middle East, "
            "and Africa, Sparrow Interactive has established itself as a truly international "
            "experiential technology company. The company's work spans real estate, retail, "
            "corporate, healthcare, and education sectors across these regions."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com/about-us/",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 9),
        text=(
            "Sparrow Interactive — Company Culture & Identity\n"
            "Sparrow is a flock of storytellers, creative thinkers and dogged innovators. "
            "They believe stories outlast a good payday, and are the only thing that can "
            "have lasting impact. They pursue methods that break free from tradition, "
            "embrace technological shifts, believe in pioneering new frontiers, and root "
            "everything they work upon in creativity.\n\n"
            "The team section on the website is titled 'Meet the Minds', reflecting "
            "the company's emphasis on creative talent and innovation. Sparrow Interactive "
            "operates with 150+ digital evangelists across specialized departments."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com/about-us/",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 11),
        text=(
            "Sparrow Interactive — North Zone Clients & Projects\n"
            "Sparrow Interactive's key clients in North India (North Zone) include "
            "Godrej, DLF, Gaurs, Ace, EMAAR, and M3M. Across these six developers alone, "
            "we have delivered over 120 projects in the last decade. "
            "Notable case studies include M3M Capital (Sec 113, Gurgaon) and Gaurs Trecento (Noida)."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com/projects/",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 12),
        text=(
            "Sparrow Interactive — West Zone Clients & Projects\n"
            "Sparrow Interactive's key clients in West India (West Zone) include "
            "Reliance, Adani Enterprises, Runwal Group, Paradise Group, Purvankara, and Godrej. "
            "Across these six developers alone, we have delivered over 200 projects in the last decade. "
            "Our West Zone work spans immersive experiences, 3D walkthroughs, and "
            "precision-crafted scale models for leading western India developers."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com/projects/",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 13),
        text=(
            "Sparrow Interactive — Experience Centre & Office Visits\n"
            "Yes, you can visit Sparrow Interactive's office to experience our work firsthand. "
            "We welcome clients and prospective partners to our headquarters at "
            "7th Floor, Plot No 19A, Filmcity, Sector 16A, Noida - 201301, Uttar Pradesh, India "
            "to see live demonstrations of our experience centres, scale models, interactive solutions, "
            "and immersive technology setups. Visiting in person is the best way to understand "
            "the quality and impact of our work. "
            "To schedule a visit, contact us at biz@sparrowi.com or call +91-9810119956."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com/contact-us/",
    ),
    Chunk(
        id=_make_chunk_id("sparrowi.com", "website", 15),
        text=(
            "Sparrow Interactive — Team Structure, Account Management & Project Execution\n"
            "Sparrow Interactive operates with 150+ digital evangelists across specialized departments:\n\n"
            "Core Departments:\n"
            "- 3D Visualization\n"
            "- Scale Models\n"
            "- Interactive Tech\n"
            "- Film Production\n"
            "- Digital Media\n"
            "- Corporate Communication\n"
            "- Human Resources\n"
            "- Marketing & Outreach\n"
            "- Business Strategy\n"
            "- Middle East Operations\n\n"
            "Account Management: Each key account is assigned a dedicated project manager "
            "as the single point of contact. For the biggest accounts, senior leadership "
            "is directly involved in strategic direction.\n\n"
            "Project Execution: Projects follow a structured process — Discovery & Briefing, "
            "Concept Design, Production & Development (across parallel departments), "
            "Integration & Testing, Installation & Handover, and Post-Delivery Support. "
            "The project manager coordinates across all departments throughout."
        ),
        table="sparrowi.com",
        chunk_type="website",
        url="https://www.sparrowi.com/about-us/",
    ),
]
