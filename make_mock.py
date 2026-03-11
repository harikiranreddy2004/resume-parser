import docx
doc = docx.Document()
doc.add_paragraph('Test resume text.')
doc.save('test_mock.docx')
