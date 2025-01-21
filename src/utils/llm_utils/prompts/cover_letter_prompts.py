prompt_cover_letter_template = """
- **Template to Use**
```
<section id="cover-letter">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
        <div>
            <p>[Your Name]</p>
            <p>[Your Address]</p>
            <p>[City, State ZIP]</p>
            <p>[Your Email]</p>
            <p>[Your Phone Number]</p>
        </div>
        <div style="text-align: right;">
            <p>[Company Name]</p>
        </div>
    </div>
    <div>
    <p>Dear [Recipient Team],</p>
    <p>[Opening paragraph: Introduce yourself and state the position you are applying for.]</p>
    <p>[Body paragraphs: Highlight your qualifications, experiences, and how they align with the job requirements.]</p>
    <p>[Closing paragraph: Express your enthusiasm for the position and thank the recipient for their consideration.]</p>
    <p>Sincerely,</p>
    <p>[Your Name]</p>
    <p>[Date]</p>
    </div>
</section>
```
The results should be provided in html format, Provide only the html code for the cover letter, without any explanations or additional text and also without ```html ```
"""



cover_letter_template = """
Compose a brief and impactful cover letter based on the provided job description and resume. The letter should be no longer than three paragraphs and should be written in a professional, yet conversational tone. Avoid using any placeholders, and ensure that the letter flows naturally and is tailored to the job.

Analyze the job description to identify key qualifications and requirements. Introduce the candidate succinctly, aligning their career objectives with the role. Highlight relevant skills and experiences from the resume that directly match the job’s demands, using specific examples to illustrate these qualifications. Reference notable aspects of the company, such as its mission or values, that resonate with the candidate’s professional goals. Conclude with a strong statement of why the candidate is a good fit for the position, expressing a desire to discuss further.

Please write the cover letter in a way that directly addresses the job role and the company’s characteristics, ensuring it remains concise and engaging without unnecessary embellishments. The letter should be formatted into paragraphs and should not include a greeting or signature.

## Rules:
- Do not include any introductions, explanations, or additional information.

## Details :
- **Job Description:**
```
{job_description}
```
- **My resume:**
```
{resume}
```
"""+ prompt_cover_letter_template