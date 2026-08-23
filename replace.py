content = open('templates/index.html', 'r', encoding='utf-8').read()
content = content.replace('class="hero-image" ', 'class="hero-image" fetchpriority="high" ')
open('templates/index.html', 'w', encoding='utf-8').write(content)
