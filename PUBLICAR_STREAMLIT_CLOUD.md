# Publicação no Streamlit Cloud - imagens do aplicativo

Para as imagens aparecerem no aplicativo publicado, envie para o GitHub/Streamlit Cloud estes itens juntos:

- streamlit_app.py
- requirements.txt
- pasta data inteira
- pasta assets inteira

Estrutura esperada:

Aplicativo/
  streamlit_app.py
  requirements.txt
  data/
    slides.json
    slides-data.js
    registros_residuos.json
  assets/
    images/
      apresentacao/
      pptx/
      image1.png ...

Observações importantes:

- Não publique somente o arquivo streamlit_app.py, porque as fotos ficam dentro de assets/images.
- O Streamlit Cloud diferencia maiúsculas e minúsculas. Use exatamente assets/images, em letras minúsculas.
- Depois de atualizar no GitHub, no Streamlit Cloud clique em Reboot app ou Manage app > Reboot.
- Se ainda aparecer sem imagem, abra a seção Galeria e veja o diagnóstico. Ele deve mostrar se assets/images foi encontrado.

Correção aplicada no código:

- O app agora procura imagens também dentro das subpastas assets/images/apresentacao e assets/images/pptx.
- O app também procura slides em mais de uma pasta data.
- Se slides.json ou slides-data.js não forem encontrados, o app tenta montar a galeria a partir das imagens disponíveis.
