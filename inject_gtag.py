import os

files_to_update = [
    'templates/base.html', 
    'templates/admin/base.html', 
    'templates/404.html', 
    'templates/500.html', 
    'templates/waiting.html'
]

gtag_script = '''<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-6RLY88HN0K"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-6RLY88HN0K');
</script>'''

for filepath in files_to_update:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'G-6RLY88HN0K' not in content:
            # Insert after the existing GTM script or at the top of <head>
            if '<!-- End Google Tag Manager -->' in content:
                content = content.replace('<!-- End Google Tag Manager -->', '<!-- End Google Tag Manager -->\n\n    ' + gtag_script)
            elif '<head>' in content:
                content = content.replace('<head>', '<head>\n    ' + gtag_script)
                
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {filepath}")
        else:
            print(f"Already updated {filepath}")
