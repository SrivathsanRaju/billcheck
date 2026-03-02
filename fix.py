for path in ['backend/app/services/invoice_extractor.py', 'backend/app/services/contract_extractor.py']:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(
        'text.split("`json").split("`")[0]',
        'text.split("`json").split("`")[0]'
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed: {path}')
