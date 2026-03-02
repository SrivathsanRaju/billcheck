files = [
    'backend/app/services/invoice_extractor.py',
    'backend/app/services/contract_extractor.py'
]
for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    c = c.replace('split("' + chr(96)*3 + 'json").split("' + chr(96)*3 + '")[1]', 'split("' + chr(96)*3 + 'json")[1].split("' + chr(96)*3 + '")[0]')
    c = c.replace('split("' + chr(96)*3 + '").split("' + chr(96)*3 + '")[0]', 'split("' + chr(96)*3 + '")[1].split("' + chr(96)*3 + '")[0]')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print('Fixed:', path)
