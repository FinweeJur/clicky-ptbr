# Referências — arte do bicho-preguiça (estilo cartoon)

Registra de onde veio a forma e a cor do bichinho do companheiro Seu Nonô, o
critério de similaridade e a ressalva de uso.

## Estilo atual: cartoon

A primeira versão era realista (baseada em foto). A pedido do dono, a arte
passou ao estilo **cartoon**: corpo redondo pendurado de cabeça para baixo num
galho com folhas, rosto creme e contorno escuro.

## Referência

Imagem cartoon enviada pelo dono (origem Pinterest), analisada **apenas para
traçar forma e cor**. O arquivo **não** é versionado aqui; fica em
`CLICKY_REF_DIR` (padrão: `C:\Users\teste\AppData\Local\Temp\opencode\preguica-ref`).

⚠️ **Ressalva de uso:** a forma do desenho deriva dessa referência de terceiro.
Para uso comercial ou redistribuição, trocar por um desenho próprio ou obter
licença. A arte é gerada por código em `assets/make_preguica.py`.

## Onde a imagem-fonte aparece (só no repositório, no doc)

- `ref_brave.jpg` — imagem cartoon do bichinho (Pinterest, via Brave).

## Como a forma foi capturada

`assets/make_preguica.py` traz a **grade de 36×29** já traçada da referência,
EMBUTIDA no código (`BASE`), então a arte sai sem depender da imagem. A paleta
de 15 tons foi amostrada da própria referência.

## Critério de similaridade (medido: 98,7%)

`python assets/make_preguica.py --check` mede, contra a referência:

- **IoU da silhueta** — nossa forma x a da referência;
- **similaridade de cor** — 1 − erro médio de cor (distância redmean).

E exige **composto = 0,5·IoU + 0,5·cor ≥ 0,95**.

Medição de 30/09/2026: **IoU 1,00 · cor 0,973 · composto 0,987**.

## Movimento (movimento dos pixels)

Os seis quadros saem do mesmo desenho por operações de pixel: `alcanca` e
`puxa` deslizam o corpo para os lados (balanço), `chega` desce o bicho e
`dorme` fecha os olhos e desce. O overlay do app soma a isso o voo em arco
para alcançar os locais (`ui/overlay.py`).

## Paleta

Ver `assets/preguica/paleta.json`. Tons principais: corpo `#D7A270`, sombra
`#B5785A`, contorno vinho `#5A0E2B`, pelo claro/face `#EDD4AA`, folha `#84C574`.
