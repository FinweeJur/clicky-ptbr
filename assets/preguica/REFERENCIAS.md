# Referências — arte do bicho-preguiça

Este documento registra de onde vieram a forma e a cor do bichinho do
companheiro Seu Nonô, e qual critério diz que o desenho "parece o bastante".

## Espécie

**Bicho-preguiça-de-garganta-marrom** (*Bradypus variegatus*), a preguiça
mais comum no Brasil. É a de três dedos, maior e de movimento ainda mais
lento que a de dois dedos.

## Anatomia usada no desenho

Dados de [Sloth — Wikipedia](https://en.wikipedia.org/wiki/Sloth), acesso em
30/09/2026:

- Corpo de 60 a 80 cm; membros longos; cabeça arredondada com orelhas
  mínimas.
- Nos três dedos, os **braços são cerca de 50% mais longos que as pernas** —
  por isso o desenho tem braços longos e pernas curtas.
- Garras **longas e curvas**, usadas para pendurar-se. No desenho, três
  garras por mão.
- Pelagem farta que hospeda **algas verdes simbióticas**, o que dá o tom
  esverdeado e a camuflagem.
- Movimento lento e deliberado — é o que dá o ritmo do bichinho no app.

## Fotos analisadas (cor e silhueta)

Imagens do Wikimedia Commons, usadas **somente para amostragem de cor e de
proporção**. Nenhuma é redistribuída neste repositório; a arte é original,
desenhada por código em `assets/make_preguica.py`.

| Arquivo de análise | Obra | Autor | Licença | Fonte |
|---|---|---|---|---|
| `ref1_bradypus.jpg` | *Bicho-preguiça 3* (*Bradypus variegatus*) | — | Wikimedia Commons | [Special:FilePath](https://commons.wikimedia.org/wiki/Special:FilePath/Bicho-pregui%C3%A7a_3.jpg) |
| `ref2_alimentando.jpg` | *MC Drei-Finger-Faultier* | — | Wikimedia Commons | [Special:FilePath](https://commons.wikimedia.org/wiki/Special:FilePath/MC_Drei-Finger-Faultier.jpg) |
| `ref3_choloepus.jpg` | *Choloepus hoffmanni* (Puerto Viejo, CR) | — | Wikimedia Commons | [Special:FilePath](https://commons.wikimedia.org/wiki/Special:FilePath/Choloepus_hoffmanni_(Puerto_Viejo,_CR)_crop.jpg) |
| `ref4_atravessando.jpg` | *Three-toed sloth crossing road in Costa Rica* | — | Wikimedia Commons | [Special:FilePath](https://commons.wikimedia.org/wiki/Special:FilePath/Three-toed_sloth_crossing_road_in_Costa_Rica.jpg) |

Para reanalisar as cores de qualquer foto:

```bash
CLICKY_REF_DIR=<pasta-das-fotos> python assets/make_preguica.py --check --contato folha.png
```

## Critério de similaridade

`assets/make_preguica.py --check` mede e exige:

1. **Paleta** — toda cor usada fica a no máximo ΔE 22 do tom mais próximo da
   paleta amostrada das fotos.
2. **Proporção** — braços ≥ 45% da altura; cabeça entre 40% e 70% da largura
   do corpo.
3. **Leitura** — ao menos 3 faixas de valor de luminância; face clara ≥ 5%
   dos pixels visíveis.
4. **Contraste** — contorno escuro contra fundo claro **e** aro claro contra
   fundo escuro, ambos ≥ 40 de diferença de luminância. É a borda dupla que
   mantém o bichinho visível sobre qualquer janela.

## Paleta final

Ver `assets/preguica/paleta.json`. Tons principais: pelagem escura `#3E3025`,
média `#6D5A43`, clara `#A79878`; face `#F0E8D8`; máscara `#2A2017`; alga
`#6E8F4C`; garra `#C9BFA8`; contorno `#241C14`; aro `#F2ECDD`.
