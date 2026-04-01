import fitz, pptx, os

pdf_path = r"D:\py_work\2026\AirConditioningDesign\air-conditioning-design-paper\defenses\beamer\college-beamer\air_conditioning_design_defense.pdf"
doc = fitz.open(pdf_path)
prs = pptx.Presentation()
prs.slide_width, prs.slide_height = pptx.util.Inches(10), pptx.util.Inches(7.5) # 可按需调整比例

for page in doc:
    pix = page.get_pixmap(dpi=300)
    img_path = "temp.png"
    pix.save(img_path)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_picture(img_path, 0, 0, prs.slide_width, prs.slide_height)

prs.save(pdf_path.replace(".pdf", ".pptx"))
os.remove("temp.png")