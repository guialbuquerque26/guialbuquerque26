"""Gera banner.gif a partir de banner.svg, simulando a digitação no terminal.

Requer: pip install pillow playwright (usa o Chrome já instalado).
Uso: python gerar_banner.py
"""
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

PASTA_ASSETS = Path(__file__).resolve().parent.parent
LARGURA, ALTURA = 1200, 420
COMANDO = "guilherme --perfil"
COMANDO_SAIDA = "clear"
SAIDAS = ["nome", "cargo", "pilha", "foco"]
COR_TRANSPARENTE = (255, 0, 255)
X_COMANDO, Y_CURSOR_TOPO, Y_CURSOR_FINAL = 82, 82, 360
LARGURA_LETRA_MEDIDA = "document.getElementById('comando').getComputedTextLength() / 18"


def aplicar_estado(
    pagina: Page,
    comando: str = "",
    saidas: tuple[str, ...] = (),
    final: bool = False,
    comando_final: str = "",
    cursor: bool = True,
    largura_letra: float = 0,
) -> None:
    texto_ativo = comando_final if final else comando
    x_cursor = X_COMANDO + len(texto_ativo) * largura_letra + (4 if texto_ativo else 0)
    y_cursor = Y_CURSOR_FINAL if final else Y_CURSOR_TOPO
    pagina.evaluate(
        """([comando, comandoFinal, saidas, todasSaidas, final, cursor, x, y]) => {
            const el = (id) => document.getElementById(id);
            el('comando').textContent = comando;
            el('comando-final').textContent = comandoFinal;
            todasSaidas.forEach((id) => {
                el(id).style.display = saidas.includes(id) ? '' : 'none';
            });
            el('prompt-final').style.display = final ? '' : 'none';
            el('cursor').style.display = cursor ? '' : 'none';
            el('cursor').setAttribute('x', x);
            el('cursor').setAttribute('y', y);
        }""",
        [comando, comando_final, list(saidas), SAIDAS, final, cursor, x_cursor, y_cursor],
    )


def capturar(pagina: Page) -> Image.Image:
    """Tira o quadro e troca os cantos transparentes por uma cor reservada."""
    imagem = Image.open(BytesIO(pagina.screenshot(omit_background=True))).convert("RGBA")
    mascara = imagem.getchannel("A").point(lambda valor: 255 if valor >= 128 else 0)
    quadro = Image.new("RGB", imagem.size, COR_TRANSPARENTE)
    quadro.paste(imagem.convert("RGB"), mask=mascara)
    return quadro


def linha_do_tempo():
    """Produz (estado da tela, duração em milissegundos) de cada passo.

    Começa com a tela completa para o primeiro quadro já mostrar o perfil.
    """
    tela_completa = {"comando": COMANDO, "saidas": tuple(SAIDAS), "final": True}
    for _ in range(6):
        yield {**tela_completa, "cursor": True}, 550
        yield {**tela_completa, "cursor": False}, 550
    for tamanho in range(1, len(COMANDO_SAIDA) + 1):
        yield {**tela_completa, "comando_final": COMANDO_SAIDA[:tamanho]}, 90
    yield {**tela_completa, "comando_final": COMANDO_SAIDA}, 350

    yield {}, 700
    for tamanho in range(1, len(COMANDO) + 1):
        yield {"comando": COMANDO[:tamanho]}, 70
    yield {"comando": COMANDO}, 350
    yield {"comando": COMANDO, "cursor": False}, 180
    for quantidade in range(1, len(SAIDAS) + 1):
        yield {"comando": COMANDO, "saidas": tuple(SAIDAS[:quantidade]), "cursor": False}, 180


def gerar_quadros() -> tuple[list[Image.Image], list[int]]:
    svg = (PASTA_ASSETS / "banner.svg").read_text(encoding="utf-8")
    html = (
        '<!doctype html><meta charset="utf-8">'
        f"<style>html,body{{margin:0;background:transparent}}svg{{display:block}}</style>{svg}"
    )
    quadros: list[Image.Image] = []
    duracoes: list[int] = []
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(channel="chrome")
        pagina = navegador.new_page(viewport={"width": LARGURA, "height": ALTURA})
        pagina.set_content(html)
        largura_letra = pagina.evaluate(LARGURA_LETRA_MEDIDA)
        for estado, duracao in linha_do_tempo():
            aplicar_estado(pagina, largura_letra=largura_letra, **estado)
            quadro = capturar(pagina)
            if quadros and quadro.tobytes() == quadros[-1].tobytes():
                duracoes[-1] += duracao
                continue
            quadros.append(quadro)
            duracoes.append(duracao)
        navegador.close()
    return quadros, duracoes


def salvar_gif(quadros: list[Image.Image], duracoes: list[int], destino: Path) -> None:
    paleta = quadros[0].quantize(colors=128, dither=Image.Dither.NONE)
    paletizados = [q.quantize(palette=paleta, dither=Image.Dither.NONE) for q in quadros]
    paletizados[0].save(
        destino,
        save_all=True,
        append_images=paletizados[1:],
        duration=duracoes,
        loop=0,
        optimize=False,
        transparency=paletizados[0].getpixel((0, 0)),
        disposal=1,
    )


def main() -> None:
    quadros, duracoes = gerar_quadros()
    destino = PASTA_ASSETS / "banner.gif"
    salvar_gif(quadros, duracoes, destino)
    print(
        f"{destino.name}: {len(quadros)} quadros, {sum(duracoes) / 1000:.1f}s, "
        f"{destino.stat().st_size / 1024:.0f} KB"
    )


if __name__ == "__main__":
    main()
