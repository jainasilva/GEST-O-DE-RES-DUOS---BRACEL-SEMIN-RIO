from __future__ import annotations

import json
import os
import re
import unicodedata
import uuid
from datetime import date
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "assets" / "images"
HERO_IMAGE_FILE = IMAGES_DIR / "apresentacao" / "pres_slide01.png"
REGISTROS_FILE = DATA_DIR / "registros_residuos.json"
AVISO_LEGAL_DISCLAIMER = (
    "Aviso Legal: Este trabalho foi desenvolvido para fins exclusivamente acadêmicos. "
    "Todos os dados, nomes, marcas, logotipos e imagens das empresas citadas foram utilizados "
    "de forma meramente ilustrativa e didática. Este material não foi elaborado, endossado "
    "ou aprovado pela(s) empresa(s) em questão, mantendo-se intactos todos os seus direitos "
    "de imagem, propriedade intelectual e marcas registradas."
)

IMAGENS_SECOES = {
    "dashboard": [
        ("apresentacao/pres_slide01.png", "Visão geral da unidade industrial"),
        ("apresentacao/pres_slide25.png", "Indicadores de desempenho e verificação"),
    ],
    "residuos": [
        ("apresentacao/pres_slide05.jpg", "Gestão de resíduos industriais"),
        ("apresentacao/pres_slide06.png", "Tratamento e destinação de resíduos"),
    ],
    "tratamento": [
        ("apresentacao/pres_slide06.png", "Fluxo simplificado do processo produtivo"),
        ("apresentacao/pres_slide07.jpg", "Tratamento de água e efluentes"),
        ("apresentacao/pres_slide08.png", "Dados operacionais de água, efluentes e resíduos"),
    ],
    "planos": [
        ("apresentacao/pres_slide17.png", "Passivo ambiental: erosão"),
        ("apresentacao/pres_slide18.jpg", "Passivo ambiental: vazamento de óleo"),
        ("apresentacao/pres_slide20.png", "Plano de ação e cronograma dos passivos"),
    ],
    "prad": [
        ("apresentacao/pres_slide17.png", "Área degradada em recuperação"),
        ("apresentacao/pres_slide20.png", "Cronograma de execução do PRAD"),
        ("apresentacao/pres_slide21.png", "Tabela de acompanhamento técnico"),
    ],
}

TIPOS_RESIDUO_POR_CLASSE = {
    "Classe I": [
        "Óleos lubrificantes",
        "Solventes contaminados",
        "Resíduos químicos",
        "Tintas, vernizes e solventes",
        "Lodos contaminados (químicos)",
        "Embalagens contaminadas com produtos perigosos",
        "Absorventes e EPIs contaminados",
        "Filtros de óleo usados",
        "Pilhas e baterias",
        "Solo contaminado",
    ],
    "Classe IIA": [
        "Cinzas (CAL) industriais",
        "Lodo biológico",
        "Biomassa",
        "Resíduos orgânicos industriais",
        "Borra de processo não inerte",
        "Madeira tratada",
        "Rejeitos de varrição industrial",
        "Lodos de ETE não perigosos",
        "Resíduos têxteis industriais",
        "Borracha não reciclável",
    ],
    "Classe IIB": [
        "Resíduos recicláveis",
        "Papel e papelão limpos",
        "Plástico rígido limpo",
        "Vidro",
        "Sucata metálica limpa",
        "Entulho de concreto",
        "Resíduos cerâmicos",
        "Areia limpa de varrição",
        "Solo limpo de escavação",
        "Paletes de madeira sem contaminação",
    ],
}

CLASSES_RESIDUO = list(TIPOS_RESIDUO_POR_CLASSE.keys())
TIPOS_RESIDUO = [tipo for classe in CLASSES_RESIDUO for tipo in TIPOS_RESIDUO_POR_CLASSE[classe]]
CLASSE_POR_TIPO = {tipo: classe for classe, tipos in TIPOS_RESIDUO_POR_CLASSE.items() for tipo in tipos}

DESTINACOES = [
    "Reciclagem",
    "Coprocessamento",
    "Reaproveitamento energético",
    "Aterro industrial licenciado",
    "Tratamento externo especializado",
]

STATUS_REGISTRO = [
    "Aguardando coleta",
    "Em transporte",
    "Destinado",
    "Não conformidade",
]

SAMPLE_REGISTROS = [
    {
        "id": "r1",
        "data": "2026-05-10",
        "tipo": "Cinzas (CAL) industriais",
        "classe": "Classe IIA",
        "origem": "Caldeira de recuperação",
        "quantidade": 850.0,
        "destino": "Reaproveitamento energético",
        "status": "Destinado",
    },
    {
        "id": "r2",
        "data": "2026-05-11",
        "tipo": "Resíduos recicláveis",
        "classe": "Classe IIB",
        "origem": "Área administrativa",
        "quantidade": 210.0,
        "destino": "Reciclagem",
        "status": "Destinado",
    },
    {
        "id": "r3",
        "data": "2026-05-12",
        "tipo": "Óleos lubrificantes",
        "classe": "Classe I",
        "origem": "Oficina mecânica",
        "quantidade": 120.0,
        "destino": "Tratamento externo especializado",
        "status": "Em transporte",
    },
    {
        "id": "r4",
        "data": "2026-05-13",
        "tipo": "Lodo biológico",
        "classe": "Classe IIA",
        "origem": "ETE industrial",
        "quantidade": 430.0,
        "destino": "Coprocessamento",
        "status": "Aguardando coleta",
    },
]

CORES_GRAFICOS = [
    "#0ea5e9",
    "#22c55e",
    "#06b6d4",
    "#10b981",
    "#38bdf8",
    "#4ade80",
]

RELATORIO_PRAD = {
    "empresa": "Empresa não informada",
    "empreendimento": "Unidade Industrial",
    "localizacao": "Município/UF",
    "responsavel": "Responsável técnico",
    "prazo_meses": 18,
    "area_total_ha": 14.2,
    "area_recuperacao_ha": 9.8,
    "cobertura_vegetal_pct": 68.0,
    "meta_sobrevivencia_pct": 85.0,
    "diagnostico": [
        "Presença de processos erosivos lineares em trechos de talude.",
        "Compactação superficial em acessos operacionais desativados.",
        "Necessidade de reforço na drenagem e no controle de sedimentos.",
    ],
    "metas": [
        "Estabilizar 100% dos focos erosivos prioritários em até 6 meses.",
        "Restabelecer cobertura vegetal em no mínimo 90% da área crítica.",
        "Reduzir em 80% o carreamento de sedimentos para drenagens adjacentes.",
    ],
    "acoes": [
        ("Reconformação de taludes", "Engenharia ambiental", "Alta", "Em andamento"),
        ("Implantação de canaletas e dissipadores", "Infraestrutura", "Alta", "Planejada"),
        ("Plantio de espécies nativas", "Equipe florestal", "Média", "Em andamento"),
        ("Monitoramento semestral de solo e água", "Laboratório", "Média", "Planejada"),
    ],
}

KPIS_BASE = [
    ("Resíduos para aterro (2025)", "33,1 kg/adt", "Meta 2030: -90%"),
    ("Recuperação química", "95,8%", "Meta reportada: 97%"),
    ("Consumo de água (2025)", "19,9 m³/adt", "Meta 2030: 16,6 m³/adt"),
    ("Energia renovável", "90%", "Biomassa + licor negro + solar"),
    ("CO2 removido em 2025", "3,4 mi tCO2e", "Meta 2030: 25 mi tCO2e"),
    ("Área nativa conservada", "301 mil ha", "Compromisso Um-Para-Um"),
    ("Meta de conservação", "107%", "Meta superada em 2025"),
    ("Reporting Matters", "97 pontos", "Top 15 no ciclo reportado"),
]

FLUXO_TRATAMENTO = [
    {
        "etapa": "Segregação na origem",
        "detalhe": "Separar por classe e compatibilidade para evitar mistura e reduzir risco operacional.",
    },
    {
        "etapa": "Acondicionamento seguro",
        "detalhe": "Identificar recipientes, manter rotulagem e usar embalagem compatível com o resíduo.",
    },
    {
        "etapa": "Armazenamento temporário",
        "detalhe": "Manter em área impermeabilizada, com controle de acesso e proteção contra intempéries.",
    },
    {
        "etapa": "Tratamento e destinação",
        "detalhe": "Priorizar reciclagem, coprocessamento e reaproveitamento energético antes do aterro.",
    },
    {
        "etapa": "Rastreabilidade",
        "detalhe": "Controlar MTR, CDF, transportadora e indicadores de reaproveitamento e redução de aterro.",
    },
]

PLANOS_ACAO = [
    {
        "titulo": "PRAD - Erosão Hídrica",
        "subtitulo": "Slide 18 e 19",
        "itens": [
            "Fase 1 (16/05 a 23/05): contenção emergencial com isolamento e desvio de água.",
            "Fase 2 (24/05 a 07/06): levantamento topográfico, ensaios de solo e projeto executivo.",
            "Fase 3 (08/06 a 20/07): curvas de nível, canaletas, dissipadores e check dams.",
            "Fase 4/5 (21/07 a 12/11): revegetação, biomanta e inspeções quinzenais.",
            "KPIs: cobertura vegetal >= 85% em 180 dias e redução >= 80% de sedimentos.",
        ],
    },
    {
        "titulo": "Resposta a Vazamento de Óleo",
        "subtitulo": "Slide 20 e 21",
        "itens": [
            "D0-D1: interromper fonte, isolar área e conter com barreiras/absorventes.",
            "D1-D7: reparar equipamento e validar estanqueidade antes da liberação.",
            "D7-D30: treinar equipes, checklist pré-operação e inspeções diárias.",
            "Implantar kit de mitigação obrigatório e bacia de contenção secundária.",
            "Meta: 0 recorrência e 100% dos equipamentos críticos com contenção disponível.",
        ],
    },
]

CRONOGRAMA_PASSIVOS = [
    {
        "passivo": "Erosão / voçoroca",
        "fase": "Diagnóstico",
        "acao_principal": "Levantamento de campo, topografia e delimitação da área crítica.",
        "objetivo_tecnico": "Definir causa raiz e escopo de intervenção do PRAD.",
        "inicio": "2026-06-01",
        "fim": "2026-06-15",
        "prazo_dias": 15,
        "prioridade": "Alta",
        "status": "Concluído",
        "responsavel": "Engenharia Ambiental",
    },
    {
        "passivo": "Erosão / voçoroca",
        "fase": "Contenção imediata",
        "acao_principal": "Isolamento da área, desvio de água e barreiras de sedimento.",
        "objetivo_tecnico": "Evitar evolução da feição erosiva durante o período chuvoso.",
        "inicio": "2026-06-16",
        "fim": "2026-07-05",
        "prazo_dias": 20,
        "prioridade": "Alta",
        "status": "Concluído",
        "responsavel": "Operação Florestal",
    },
    {
        "passivo": "Erosão / voçoroca",
        "fase": "Execução corretiva",
        "acao_principal": "Implantação de drenagem, dissipadores e recomposição de solo.",
        "objetivo_tecnico": "Estabilizar taludes e reduzir carreamento de sedimentos.",
        "inicio": "2026-07-06",
        "fim": "2026-08-19",
        "prazo_dias": 45,
        "prioridade": "Alta",
        "status": "Em andamento",
        "responsavel": "Infraestrutura + Meio Ambiente",
    },
    {
        "passivo": "Erosão / voçoroca",
        "fase": "Recuperação ambiental / PRAD",
        "acao_principal": "Revegetação com espécies nativas e biomanta.",
        "objetivo_tecnico": "Restabelecer cobertura vegetal funcional da área afetada.",
        "inicio": "2026-08-20",
        "fim": "2026-09-18",
        "prazo_dias": 30,
        "prioridade": "Média",
        "status": "Planejado",
        "responsavel": "Equipe de Restauração",
    },
    {
        "passivo": "Erosão / voçoroca",
        "fase": "Monitoramento",
        "acao_principal": "Inspeções e medição de cobertura vegetal e estabilidade.",
        "objetivo_tecnico": "Comprovar eficiência do PRAD e evitar recidiva.",
        "inicio": "2026-09-19",
        "fim": "2027-03-17",
        "prazo_dias": 180,
        "prioridade": "Média",
        "status": "Planejado",
        "responsavel": "SGA / Meio Ambiente",
    },
    {
        "passivo": "Vazamento de óleo",
        "fase": "Diagnóstico",
        "acao_principal": "Avaliação da origem do vazamento e área impactada.",
        "objetivo_tecnico": "Definir a severidade e o plano de resposta inicial.",
        "inicio": "2026-06-01",
        "fim": "2026-06-03",
        "prazo_dias": 3,
        "prioridade": "Alta",
        "status": "Concluído",
        "responsavel": "SSMA + Manutenção",
    },
    {
        "passivo": "Vazamento de óleo",
        "fase": "Contenção imediata",
        "acao_principal": "Conter derrame com barreiras e absorventes.",
        "objetivo_tecnico": "Eliminar risco de infiltração e carreamento para drenagem.",
        "inicio": "2026-06-04",
        "fim": "2026-06-05",
        "prazo_dias": 2,
        "prioridade": "Alta",
        "status": "Concluído",
        "responsavel": "SSMA + Operação",
    },
    {
        "passivo": "Vazamento de óleo",
        "fase": "Execução corretiva",
        "acao_principal": "Reparo do equipamento e remoção de solo contaminado.",
        "objetivo_tecnico": "Restabelecer condição segura de operação.",
        "inicio": "2026-06-06",
        "fim": "2026-06-17",
        "prazo_dias": 12,
        "prioridade": "Alta",
        "status": "Concluído",
        "responsavel": "Manutenção",
    },
    {
        "passivo": "Vazamento de óleo",
        "fase": "Recuperação ambiental / PRAD",
        "acao_principal": "Destinação de resíduos Classe I e limpeza final da área.",
        "objetivo_tecnico": "Garantir conformidade legal e encerramento da ocorrência.",
        "inicio": "2026-06-18",
        "fim": "2026-07-07",
        "prazo_dias": 20,
        "prioridade": "Média",
        "status": "Concluído",
        "responsavel": "Gestão de Resíduos",
    },
    {
        "passivo": "Vazamento de óleo",
        "fase": "Monitoramento",
        "acao_principal": "Inspeções em campo e auditoria de contenção secundária.",
        "objetivo_tecnico": "Assegurar 0 recorrência e lições aprendidas implementadas.",
        "inicio": "2026-07-08",
        "fim": "2026-10-05",
        "prazo_dias": 90,
        "prioridade": "Média",
        "status": "Em andamento",
        "responsavel": "SSMA",
    },
]

RELATORIO_RECUPERACAO = {
    "area": "Talude de drenagem - Setor Florestal Leste",
    "municipio": "Lençóis Paulista - SP",
    "referencia": "03/06/2026",
    "diagnostico": [
        "Processo erosivo em ravina com risco de evolução para voçoroca.",
        "Concentração de escoamento superficial por ausência de drenagem definitiva.",
        "Solo exposto com baixa cobertura vegetal e perda de horizonte superficial.",
        "Risco de carreamento de sedimentos para área de APP a jusante.",
    ],
    "metas": [
        "Estabilizar fisicamente 100% da feição erosiva em até 90 dias.",
        "Alcançar cobertura vegetal >= 85% em até 180 dias.",
        "Reduzir >= 80% do carreamento de sedimentos em eventos de chuva.",
        "Manter 100% de funcionalidade do sistema de drenagem implantado.",
    ],
    "cronograma": [
        {
            "fase": "Fase 1 - Contenção emergencial",
            "periodo": "16/05/2026 a 23/05/2026",
            "escopo": "Isolamento de área, desvio temporário de água e barreiras de sedimento.",
            "entregavel": "Área estabilizada provisoriamente e risco imediato reduzido.",
        },
        {
            "fase": "Fase 2 - Projeto executivo",
            "periodo": "24/05/2026 a 07/06/2026",
            "escopo": "Levantamento topográfico, ensaio e dimensionamento hidráulico.",
            "entregavel": "Projeto técnico validado e plano de obra aprovado.",
        },
        {
            "fase": "Fase 3 - Obras de recuperação",
            "periodo": "08/06/2026 a 20/07/2026",
            "escopo": "Canaletas, dissipadores, terraceamento e proteção superficial do solo.",
            "entregavel": "Drenagem definitiva implantada e erosão controlada.",
        },
        {
            "fase": "Fase 4 - Revegetação e monitoramento",
            "periodo": "21/07/2026 a 12/11/2026",
            "escopo": "Hidrossemeadura, biomanta e inspeções quinzenais.",
            "entregavel": "Cobertura vegetal consolidada e relatório de eficácia.",
        },
    ],
    "acoes": [
        {
            "acao": "Implantar drenagem superficial definitiva no trecho crítico.",
            "responsavel": "Engenharia Ambiental + Civil",
            "prazo": "20/07/2026",
            "prioridade": "Alta",
            "status": "Em andamento",
        },
        {
            "acao": "Executar recomposição de solo e proteção anti-erosiva com biomanta.",
            "responsavel": "Operação Florestal",
            "prazo": "05/08/2026",
            "prioridade": "Alta",
            "status": "Planejada",
        },
        {
            "acao": "Revegetar área degradada com espécies adaptadas e manutenção inicial.",
            "responsavel": "Equipe de Restauração",
            "prazo": "30/08/2026",
            "prioridade": "Média",
            "status": "Planejada",
        },
        {
            "acao": "Realizar monitoramento e auditoria técnica mensal por 6 meses.",
            "responsavel": "SGA / Meio Ambiente",
            "prazo": "12/11/2026",
            "prioridade": "Média",
            "status": "Planejada",
        },
    ],
    "monitoramento": [
        "Inspeções quinzenais com checklist de estabilidade geotécnica.",
        "Levantamento fotográfico em pontos fixos para rastreabilidade.",
        "Medição de cobertura vegetal e taxa de sobrevivência das mudas.",
        "Controle de sedimentos em pontos de saída de drenagem.",
        "Relatório técnico mensal com ações corretivas e preventivas.",
    ],
}

DESTINOS_VALORIZACAO = {"Reciclagem", "Coprocessamento", "Reaproveitamento energético"}

MAP_TIPO_PT_BR = {
    "Lodo biologico": "Lodo biológico",
    "Oleos lubrificantes": "Óleos lubrificantes",
    "Residuos quimicos": "Resíduos químicos",
    "Resíduos quimicos": "Resíduos químicos",
    "Residuos reciclaveis": "Resíduos recicláveis",
    "Resíduos reciclaveis": "Resíduos recicláveis",
}

MAP_DESTINO_PT_BR = {
    "Reaproveitamento energetico": "Reaproveitamento energético",
}

MAP_STATUS_PT_BR = {
    "Nao conformidade": "Não conformidade",
    "Não conformidade": "Não conformidade",
}

MOJIBAKE_MAP = {
    "Ã¡": "á",
    "Ã¢": "â",
    "Ã£": "ã",
    "Ã ": "à",
    "Ã¤": "ä",
    "Ã©": "é",
    "Ãª": "ê",
    "Ã¨": "è",
    "Ã­": "í",
    "Ã¬": "ì",
    "Ã³": "ó",
    "Ã´": "ô",
    "Ãµ": "õ",
    "Ã²": "ò",
    "Ãº": "ú",
    "Ã¹": "ù",
    "Ã§": "ç",
    "Ã": "Á",
    "Ãƒâ€š": "Ã‚",
    "ÃƒÆ’": "Ãƒ",
    "Ã€": "À",
    "Ã‰": "É",
    "ÃŠ": "Ê",
    "Ã“": "Ó",
    "Ã”": "Ô",
    "Ã•": "Õ",
    "Ãš": "Ú",
    "Ã‡": "Ç",
    "â€¢": "",
    "â€“": "-",
    "â€”": "-",
}

def aplicar_tema_css(tema: str) -> None:
    if tema == "dark":
        bg = "#081d18"
        bg_mid = "#102922"
        bg_end = "#0c221c"
        grad_a = "rgba(34, 168, 106, 0.20)"
        grad_b = "rgba(37, 142, 231, 0.22)"
        surface = "#132c24"
        surface_soft = "#17372d"
        card_a = "rgba(19, 44, 36, 0.96)"
        card_b = "rgba(23, 55, 45, 0.92)"
        ink = "#def4ea"
        ink_soft = "#9ec2b5"
        accent = "#34b879"
        accent_strong = "#5ab4ff"
        border = "#2d5749"
        line = "#2f5f50"
        input_bg = "#10231d"
        nav_chip_bg = "rgba(17, 45, 37, 0.9)"
        btn_bg = "#18362c"
        primary_grad_a = "#2f9764"
        primary_grad_b = "#2a86c6"
        shadow = "0 14px 28px rgba(0, 0, 0, 0.35)"
    else:
        bg = "#eaf5f1"
        bg_mid = "#f6fbf9"
        bg_end = "#f0f8f5"
        grad_a = "rgba(24, 138, 91, 0.12)"
        grad_b = "rgba(12, 108, 187, 0.14)"
        surface = "#ffffff"
        surface_soft = "#f2f9f6"
        card_a = "rgba(255, 255, 255, 0.96)"
        card_b = "rgba(242, 249, 246, 0.92)"
        ink = "#143327"
        ink_soft = "#4a6c5e"
        accent = "#1f7a48"
        accent_strong = "#0c6cbb"
        border = "#c8ded2"
        line = "#d8e6df"
        input_bg = "#fbfffd"
        nav_chip_bg = "rgba(255, 255, 255, 0.78)"
        btn_bg = "#eff7f3"
        primary_grad_a = "#1f7a48"
        primary_grad_b = "#239f69"
        shadow = "0 14px 30px rgba(17, 42, 34, 0.1)"

    st.markdown(
        f"""
        <style>
            .stApp {{
                --bg: {bg};
                --bg-mid: {bg_mid};
                --bg-end: {bg_end};
                --surface: {surface};
                --surface-soft: {surface_soft};
                --card-a: {card_a};
                --card-b: {card_b};
                --ink: {ink};
                --ink-soft: {ink_soft};
                --accent: {accent};
                --accent-strong: {accent_strong};
                --border: {border};
                --line: {line};
                --input-bg: {input_bg};
                --nav-chip-bg: {nav_chip_bg};
                --btn-bg: {btn_bg};
                --primary-a: {primary_grad_a};
                --primary-b: {primary_grad_b};
                --shadow: {shadow};
                color: var(--ink);
                font-family: "Bahnschrift", "Trebuchet MS", "Segoe UI", sans-serif;
                background:
                    radial-gradient(circle at 15% 20%, {grad_a}, transparent 45%),
                    radial-gradient(circle at 85% 10%, {grad_b}, transparent 36%),
                    linear-gradient(160deg, var(--bg) 0%, var(--bg-mid) 52%, var(--bg-end) 100%);
            }}
            .stApp::before,
            .stApp::after {{
                content: "";
                position: fixed;
                pointer-events: none;
                z-index: 0;
                filter: blur(2px);
            }}
            .stApp::before {{
                width: 260px;
                height: 260px;
                left: -60px;
                top: -80px;
                background: linear-gradient(140deg, rgba(31,122,72,0.22), rgba(12,108,187,0.16));
                border-radius: 40% 60% 68% 32% / 35% 33% 67% 65%;
                animation: drift 18s ease-in-out infinite;
            }}
            .stApp::after {{
                width: 320px;
                height: 320px;
                right: -120px;
                bottom: -120px;
                background: linear-gradient(120deg, rgba(12,108,187,0.24), rgba(31,122,72,0.12));
                border-radius: 64% 36% 26% 74% / 54% 64% 36% 46%;
                animation: drift 22s ease-in-out infinite reverse;
            }}
            @keyframes drift {{
                0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
                50% {{ transform: translateY(14px) rotate(6deg); }}
            }}
            .block-container {{
                position: relative;
                z-index: 1;
                width: min(1220px, 100%);
                padding-top: 1.1rem;
                padding-bottom: 2rem;
            }}
            .app-card {{
                background: linear-gradient(180deg, var(--card-a), var(--card-b));
                border: 1px solid var(--border);
                border-radius: 18px;
                box-shadow: var(--shadow);
                padding: 16px 18px;
                margin-bottom: 12px;
            }}
            .subtle {{ color: var(--ink-soft); }}
            h1, h2, h3 {{
                font-family: "Rockwell", "Cambria", serif;
                letter-spacing: 0.2px;
            }}
            .stButton > button {{
                border-radius: 9px;
                border: 1px solid var(--border);
                background: var(--btn-bg);
                color: var(--ink);
            }}
            .stButton > button:hover {{
                border-color: var(--accent);
                color: var(--accent);
            }}
            .stMetric {{
                background: linear-gradient(145deg, var(--surface), var(--surface-soft));
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 9px;
            }}
            div[data-testid="stMetricLabel"] p,
            div[data-testid="stMetricValue"] > div,
            div[data-testid="stMetricDelta"] > div {{
                color: var(--ink) !important;
                opacity: 1 !important;
            }}
            div[data-testid="stMetricDelta"] svg {{
                fill: var(--ink) !important;
                stroke: var(--ink) !important;
            }}
            div[data-testid="stHorizontalBlock"] > div {{
                min-width: 0;
            }}
            div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
                gap: 10px;
                flex-wrap: wrap;
                align-items: center;
            }}
            div[data-testid="stTabs"] [data-baseweb="tab"] {{
                background: var(--nav-chip-bg);
                border: 1px solid var(--border);
                border-radius: 999px;
                padding: 2px 8px;
                color: var(--ink);
            }}
            div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
                border-color: var(--accent);
                color: var(--accent);
                box-shadow: 0 2px 8px rgba(12,108,187,0.14);
            }}
            div[data-testid="stTabs"] [data-baseweb="tab-panel"] {{
                margin-top: 0.65rem;
                background: linear-gradient(180deg, var(--card-a), var(--card-b));
                border: 1px solid var(--border);
                border-radius: 18px;
                box-shadow: var(--shadow);
                padding: 18px 16px 16px;
            }}
            div[data-testid="stExpander"] details summary {{
                background: var(--surface-soft);
                border: 1px solid var(--border);
                border-radius: 10px;
                padding: 8px 12px;
            }}
            div[data-testid="stExpander"] details summary p,
            div[data-testid="stExpander"] details summary svg {{
                color: var(--ink) !important;
                fill: var(--ink) !important;
            }}
            .hero-card {{
                border: 1px solid var(--border);
                border-radius: 18px;
                background: linear-gradient(180deg, var(--card-a), var(--card-b));
                box-shadow: var(--shadow);
                padding: 16px 18px;
                margin-bottom: 12px;
            }}
            .hero-card h3 {{
                margin: 0 0 8px 0;
            }}
            .hero-card p {{
                margin: 0.4rem 0 0.8rem 0;
                line-height: 1.58;
                color: var(--ink-soft);
            }}
            .hero-badges {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }}
            .hero-badges span {{
                border: 1px solid var(--border);
                background: rgba(31, 122, 72, 0.12);
                color: var(--accent);
                border-radius: 999px;
                padding: 6px 10px;
                font-size: 0.82rem;
                font-weight: 700;
            }}
            .nav-chip-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin: 6px 0 2px 0;
            }}
            .nav-chip {{
                text-decoration: none;
                color: var(--ink);
                padding: 7px 10px;
                border-radius: 999px;
                background: var(--nav-chip-bg);
                border: 1px solid var(--border);
                font-size: 0.82rem;
            }}
            .section-head {{
                margin-bottom: 10px;
            }}
            .section-head h2 {{
                margin: 0;
                font-size: clamp(1.2rem, 1.5vw, 1.5rem);
            }}
            .section-head p {{
                margin: 6px 0 0;
                color: var(--ink-soft);
            }}
            .timeline-step {{
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 12px;
                background: linear-gradient(165deg, var(--surface), var(--surface-soft));
                margin-bottom: 10px;
            }}
            .timeline-step strong {{
                color: var(--accent);
            }}
            .timeline-step p {{
                margin: 7px 0 0;
                color: var(--ink-soft);
                line-height: 1.45;
            }}
            .plano-card {{
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 14px;
                background: linear-gradient(160deg, var(--surface), var(--surface-soft));
                margin-bottom: 10px;
            }}
            .plano-card h3 {{
                margin: 0 0 4px;
            }}
            .plano-card ul {{
                margin: 10px 0 0;
                padding-left: 18px;
                display: grid;
                gap: 6px;
                color: var(--ink-soft);
            }}
            div[data-testid="stDataFrame"],
            div[data-testid="stDataEditor"] {{
                border: 1px solid var(--border);
                border-radius: 12px;
                overflow: hidden;
            }}
            div[data-testid="stImage"] img {{
                border-radius: 12px;
                border: 1px solid var(--border);
                box-shadow: var(--shadow);
            }}
            div[data-testid="stWidgetLabel"] p {{
                color: var(--ink-soft);
            }}
            div[data-baseweb="input"] > div,
            div[data-baseweb="select"] > div,
            .stTextArea textarea {{
                background: var(--input-bg);
                border-color: var(--border);
                color: var(--ink);
            }}
            .st-key-theme_btn_light button,
            .st-key-theme_btn_dark button {{
                min-width: 44px;
                border-radius: 999px;
                padding: 7px 10px;
                border-color: transparent;
                background: var(--surface-soft);
                color: var(--ink-soft);
                font-weight: 700;
            }}
            .st-key-theme_btn_light,
            .st-key-theme_btn_dark {{
                margin-top: 32px;
            }}
            .st-key-theme_btn_dark {{
                margin-right: 10px;
            }}
            .back-top-wrap {{
                position: fixed;
                right: 18px;
                bottom: 16px;
                z-index: 1000;
            }}
            .back-top-link {{
                display: inline-block;
                padding: 10px 14px;
                border-radius: 999px;
                border: 1px solid var(--border);
                background: var(--surface-soft);
                color: var(--ink) !important;
                font-weight: 700;
                text-decoration: none !important;
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
            }}
            .back-top-link:hover {{
                background: var(--surface);
                border-color: var(--accent);
                color: var(--accent) !important;
            }}
            .footer-note {{
                margin-top: 12px;
                text-align: center;
                color: var(--ink-soft);
                font-size: 0.9rem;
            }}
            @media (max-width: 900px) {{
                .block-container {{
                    padding-left: 1rem;
                    padding-right: 1rem;
                }}
                .back-top-wrap {{
                    right: 12px;
                    bottom: 12px;
                }}
                .back-top-link {{
                    padding: 13px 18px;
                    font-size: 1rem;
                    min-height: 46px;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalizar_registro_pt_br(registro: dict) -> dict:
    item = dict(registro)
    tipo = str(item.get("tipo", ""))
    destino = str(item.get("destino", ""))
    status = str(item.get("status", ""))

    # Corrige grafias corrompidas de versões anteriores da base.
    tipo = tipo.replace("Res?duos", "Resíduos")
    status = status.replace("N?o", "Não")

    item["tipo"] = MAP_TIPO_PT_BR.get(tipo, tipo)
    item["destino"] = MAP_DESTINO_PT_BR.get(destino, destino)
    item["status"] = MAP_STATUS_PT_BR.get(status, status)
    return item


def carregar_registros() -> list[dict]:
    if REGISTROS_FILE.exists():
        try:
            data = json.loads(REGISTROS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [normalizar_registro_pt_br(registro) for registro in data if isinstance(registro, dict)]
        except (json.JSONDecodeError, OSError):
            pass

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REGISTROS_FILE.write_text(json.dumps(SAMPLE_REGISTROS, ensure_ascii=False, indent=2), encoding="utf-8")
    return SAMPLE_REGISTROS.copy()


def salvar_registros(registros: list[dict]) -> tuple[bool, str]:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        REGISTROS_FILE.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
        return True, ""
    except OSError as exc:
        return False, str(exc)


def registros_para_df(registros: list[dict]) -> pd.DataFrame:
    if not registros:
        return pd.DataFrame(columns=["id", "data", "tipo", "classe", "origem", "quantidade", "destino", "status"])

    df = pd.DataFrame(registros).copy()
    df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0.0)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.sort_values("data", ascending=False)
    return df


def formatar_data_br(valor: pd.Timestamp | None) -> str:
    if pd.isna(valor):
        return "-"
    return valor.strftime("%d/%m/%Y")


def formatar_numero_br(valor: float, casas: int = 1) -> str:
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def normalizar_texto_comparacao(texto: str) -> str:
    bruto = normalizar_texto(str(texto or "")).lower()
    sem_acentos = "".join(
        ch for ch in unicodedata.normalize("NFD", bruto) if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acentos).strip()


def texto_para_itens(texto: str, padrao: list[str]) -> list[str]:
    itens = [linha.strip().lstrip("-").strip() for linha in texto.splitlines() if linha.strip()]
    return itens if itens else padrao


def slug_nome_arquivo(texto: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", texto.strip().lower())
    return slug.strip("_") or "prad"


def exibir_titulo_secao(titulo: str, descricao: str) -> None:
    st.markdown(
        f"""
        <div class="section-head">
            <h2>{titulo}</h2>
            <p>{descricao}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def exibir_lista_tipos_residuos(local: str, expanded: bool = False) -> None:
    total_tipos = sum(len(tipos) for tipos in TIPOS_RESIDUO_POR_CLASSE.values())
    resumo_df = pd.DataFrame(
        [
            {"Classe": classe_nome, "Quantidade de tipos": len(TIPOS_RESIDUO_POR_CLASSE[classe_nome])}
            for classe_nome in CLASSES_RESIDUO
        ]
    )
    st.markdown(f"#### Lista de {total_tipos} tipos de resíduos por classe")
    st.dataframe(resumo_df, width="stretch", hide_index=True)

    with st.expander(f"Clique para ver a lista completa de tipos ({local})", expanded=expanded):
        for classe_nome in CLASSES_RESIDUO:
            st.markdown(f"**{classe_nome} ({len(TIPOS_RESIDUO_POR_CLASSE[classe_nome])} tipos)**")
            for tipo_nome in TIPOS_RESIDUO_POR_CLASSE[classe_nome]:
                st.write(f"- {tipo_nome}")


@st.cache_data(show_spinner=False)
def indexar_arquivos_imagem() -> dict[str, str]:
    extensoes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
    raizes = [BASE_DIR, Path.cwd(), BASE_DIR.parent, Path.cwd().parent]
    mapa: dict[str, str] = {}
    raizes_unicas: list[Path] = []
    vistos: set[str] = set()

    for raiz in raizes:
        chave = str(raiz.resolve()) if raiz.exists() else str(raiz)
        if chave in vistos:
            continue
        vistos.add(chave)
        raizes_unicas.append(raiz)

    for raiz in raizes_unicas:
        if not raiz.exists() or not raiz.is_dir():
            continue
        total_lidos = 0
        try:
            for arquivo in raiz.rglob("*"):
                total_lidos += 1
                if total_lidos > 30000:
                    break
                if arquivo.is_file() and arquivo.suffix.lower() in extensoes:
                    chave = arquivo.name.lower()
                    if chave not in mapa:
                        mapa[chave] = str(arquivo)
        except OSError:
            continue
    return mapa


def ordenar_nomes_imagem(nomes: list[str]) -> list[str]:
    padrao = re.compile(r"^image(\d+)\.(png|jpg|jpeg|webp|gif|bmp)$", re.I)

    def chave_ordenacao(nome: str) -> tuple[int, str]:
        nome_limpo = str(nome or "").strip()
        match = padrao.match(nome_limpo)
        numero = int(match.group(1)) if match else 10**9
        return (numero, nome_limpo.lower())

    return sorted([str(nome or "").strip() for nome in nomes if str(nome or "").strip()], key=chave_ordenacao)


@st.cache_data(show_spinner=False)
def carregar_imagens_locais_cache() -> dict[str, bytes]:
    extensoes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
    candidatos = [
        IMAGES_DIR,
        BASE_DIR / "assets" / "images",
        BASE_DIR / "Assets" / "images",
        Path.cwd() / "assets" / "images",
        Path.cwd() / "Assets" / "images",
    ]

    diretorios: list[Path] = []
    vistos: set[str] = set()
    for pasta in candidatos:
        chave = str(pasta.resolve()) if pasta.exists() else str(pasta)
        if chave in vistos:
            continue
        vistos.add(chave)
        diretorios.append(pasta)

    imagens: dict[str, bytes] = {}
    for pasta in diretorios:
        if not pasta.exists() or not pasta.is_dir():
            continue
        try:
            arquivos = sorted([arq for arq in pasta.iterdir() if arq.is_file()])
        except OSError:
            continue

        for arquivo in arquivos:
            if arquivo.suffix.lower() not in extensoes:
                continue
            chave = arquivo.name.lower()
            if chave in imagens:
                continue
            try:
                imagens[chave] = arquivo.read_bytes()
            except OSError:
                continue

    return imagens


def obter_bytes_imagem_local(nome_arquivo: str) -> bytes | None:
    nome_base = extrair_nome_arquivo_imagem(nome_arquivo).lower()
    if not nome_base:
        return None
    return carregar_imagens_locais_cache().get(nome_base)


def normalizar_base_url(url: str) -> str:
    return str(url or "").strip().rstrip("/")


def extrair_nome_arquivo_imagem(referencia: str) -> str:
    texto = str(referencia or "").strip()
    if not texto:
        return ""
    texto = texto.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    if texto.startswith(("http://", "https://")):
        return texto.rsplit("/", 1)[-1]
    return Path(texto).name


def tokenizar_slug(texto: str) -> list[str]:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", str(texto or "").strip().lower()).strip("-")
    return [parte for parte in slug.split("-") if parte]


def host_execucao() -> str:
    host = ""

    def limpar_host(valor: str) -> str:
        txt = str(valor or "").strip()
        if not txt or txt.lower() in {"none", "null", "undefined"}:
            return ""
        return txt

    try:
        host = limpar_host(st.context.headers.get("host", ""))
    except Exception:
        host = ""
    if not host:
        try:
            host = limpar_host(st.context.headers.get("Host", ""))
        except Exception:
            host = ""
    if not host:
        for chave_env in ("STREAMLIT_APP_URL", "APP_URL", "PUBLIC_URL"):
            valor = limpar_host(os.getenv(chave_env, ""))
            if valor:
                host = valor.split("://", 1)[-1].split("/", 1)[0].strip()
                break
    if not host:
        try:
            url_ctx = limpar_host(st.context.url)
            if url_ctx:
                host = url_ctx.split("://", 1)[-1].split("/", 1)[0].strip()
        except Exception:
            host = ""
    if ":" in host:
        host = host.split(":", 1)[0]
    return host.lower()


def inferir_bases_url_streamlit_cloud() -> list[str]:
    host = host_execucao()
    if not host.endswith(".streamlit.app"):
        return []

    subdominio = host.split(".", 1)[0]
    partes = [p for p in subdominio.split("-") if p]
    if len(partes) < 4:
        return []

    # A URL padrão do Streamlit Cloud termina com um hash aleatório.
    corpo = partes[:-1]
    app_tokens = tokenizar_slug(Path(__file__).stem)
    if not app_tokens:
        app_tokens = ["streamlit", "app"]

    candidatos: list[str] = []
    max_owner_tokens = min(4, len(corpo) - 2)
    for owner_fim in range(1, max_owner_tokens + 1):
        for repo_fim in range(owner_fim + 1, len(corpo)):
            owner = "-".join(corpo[:owner_fim])
            repo = "-".join(corpo[owner_fim:repo_fim])
            cauda = corpo[repo_fim:]
            if not owner or not repo or not cauda:
                continue

            for idx in range(0, len(cauda) - len(app_tokens) + 1):
                if cauda[idx : idx + len(app_tokens)] != app_tokens:
                    continue
                sufixo = cauda[idx + len(app_tokens) :]
                branches = ["main", "master"]
                if sufixo:
                    branches.insert(0, "-".join(sufixo))
                for branch in branches:
                    if not branch:
                        continue
                    candidatos.append(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/assets/images")

    bases_unicas: list[str] = []
    vistos: set[str] = set()
    for base in candidatos:
        if base not in vistos:
            vistos.add(base)
            bases_unicas.append(base)
    return bases_unicas


@st.cache_data(show_spinner=False)
def listar_bases_url_imagem() -> list[str]:
    bases: list[str] = []

    try:
        base_secret = normalizar_base_url(str(st.secrets.get("IMAGE_BASE_URL", "")))
    except Exception:
        base_secret = ""
    if base_secret:
        bases.append(base_secret)

    base_env = normalizar_base_url(os.getenv("IMAGE_BASE_URL", ""))
    if base_env:
        bases.append(base_env)

    repo = normalizar_base_url(os.getenv("GITHUB_REPOSITORY", ""))
    branch_env = normalizar_base_url(os.getenv("GITHUB_REF_NAME", ""))
    if repo:
        branches = [branch_env, "main", "master"]
        for branch in branches:
            if branch:
                bases.append(f"https://raw.githubusercontent.com/{repo}/{branch}/assets/images")

    bases.extend(inferir_bases_url_streamlit_cloud())

    bases_unicas: list[str] = []
    vistos: set[str] = set()
    for base in bases:
        if base and base not in vistos:
            vistos.add(base)
            bases_unicas.append(base)
    return bases_unicas


@st.cache_data(show_spinner=False, ttl=3600)
def url_imagem_disponivel(url: str) -> bool:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = Request(url, method="HEAD", headers=headers)
        with urlopen(req, timeout=5) as resposta:
            status = getattr(resposta, "status", 200)
            return int(status) < 400
    except HTTPError as exc:
        if exc.code == 404:
            return False
    except (URLError, OSError, ValueError):
        pass

    try:
        req = Request(url, headers={**headers, "Range": "bytes=0-0"})
        with urlopen(req, timeout=5) as resposta:
            status = getattr(resposta, "status", 200)
            return int(status) < 400
    except (HTTPError, URLError, OSError, ValueError):
        return False


def resolver_caminho_imagem(nome_arquivo: str) -> Path | str | None:
    referencia = str(nome_arquivo or "").strip()
    if not referencia:
        return None

    if referencia.startswith(("http://", "https://")):
        return referencia

    nome_base = extrair_nome_arquivo_imagem(referencia)
    nome_busca = nome_base or referencia
    candidatos = [
        IMAGES_DIR / referencia,
        IMAGES_DIR / nome_busca,
        BASE_DIR / "assets" / "images" / referencia,
        BASE_DIR / "assets" / "images" / nome_busca,
        BASE_DIR / "Assets" / "images" / referencia,
        BASE_DIR / "Assets" / "images" / nome_busca,
        Path.cwd() / "assets" / "images" / referencia,
        Path.cwd() / "assets" / "images" / nome_busca,
        Path.cwd() / "Assets" / "images" / referencia,
        Path.cwd() / "Assets" / "images" / nome_busca,
    ]
    for caminho in candidatos:
        if caminho.exists() and caminho.is_file():
            return caminho

    nome_lower = nome_busca.lower()
    mapa = indexar_arquivos_imagem()
    caminho_mapeado = mapa.get(nome_lower)
    if caminho_mapeado:
        caminho = Path(caminho_mapeado)
        if caminho.exists() and caminho.is_file():
            return caminho

    primeira_url = None
    for base in listar_bases_url_imagem():
        url = f"{base}/{nome_busca}"
        if primeira_url is None:
            primeira_url = url
        if url_imagem_disponivel(url):
            return url
    if primeira_url:
        return primeira_url
    return None


def listar_referencias_imagem(nome_arquivo: str) -> list[Path | str]:
    referencia = str(nome_arquivo or "").strip()
    if not referencia:
        return []

    candidatos: list[Path | str] = []
    vistos: set[str] = set()

    def registrar(item: Path | str) -> None:
        chave = str(item)
        if chave not in vistos:
            vistos.add(chave)
            candidatos.append(item)

    resolvida = resolver_caminho_imagem(referencia)
    if resolvida:
        registrar(resolvida)

    nome_base = extrair_nome_arquivo_imagem(referencia)
    if referencia.startswith(("http://", "https://")):
        registrar(referencia)
    else:
        if nome_base:
            for base in listar_bases_url_imagem():
                registrar(f"{base}/{nome_base}")

    return candidatos


def exibir_imagem_segura(arquivo: Path | str | bytes, legenda: str | None = None) -> bool:
    try:
        if isinstance(arquivo, bytes):
            st.image(arquivo, caption=legenda, width="stretch")
        elif isinstance(arquivo, Path):
            st.image(arquivo.read_bytes(), caption=legenda, width="stretch")
        else:
            st.image(arquivo, caption=legenda, width="stretch")
        return True
    except Exception:
        return False


def exibir_imagem_por_nome(nome_arquivo: str, legenda: str | None = None) -> bool:
    imagem_local = obter_bytes_imagem_local(nome_arquivo)
    if imagem_local:
        return exibir_imagem_segura(imagem_local, legenda)

    referencias = listar_referencias_imagem(nome_arquivo)
    if not referencias:
        return False
    for idx, referencia in enumerate(referencias):
        if exibir_imagem_segura(referencia, legenda if idx == 0 else None):
            return True
    return False


def exibir_mosaico_imagens(secao: str, titulo: str = "Imagens de referência") -> None:
    imagens = IMAGENS_SECOES.get(secao, [])
    if not imagens:
        return

    st.markdown(f"**{titulo}**")
    total_carregadas = 0
    for i in range(0, len(imagens), 3):
        grupo = imagens[i : i + 3]
        colunas = st.columns(len(grupo))
        for col, (nome_arquivo, legenda) in zip(colunas, grupo):
            with col:
                if exibir_imagem_por_nome(nome_arquivo, legenda):
                    total_carregadas += 1
                else:
                    st.caption(f"Falha ao carregar: {nome_arquivo}")

    if total_carregadas == 0:
        st.info("Imagens não encontradas no deploy. Verifique se a pasta `assets/images` foi enviada ao GitHub.")
        with st.expander("Diagnóstico de imagens", expanded=False):
            bases = listar_bases_url_imagem()
            host = host_execucao()
            bases_inferidas = inferir_bases_url_streamlit_cloud()
            st.code(
                "\n".join(
                    [
                        f"BASE_DIR: {BASE_DIR}",
                        f"CWD: {Path.cwd()}",
                        f"Host da sessão: {host or 'indisponível'}",
                        f"IMAGES_DIR esperado: {IMAGES_DIR}",
                        f"Arquivos de imagem detectados no repositório: {len(indexar_arquivos_imagem())}",
                        f"Bases inferidas via URL do Streamlit: {bases_inferidas if bases_inferidas else 'nenhuma'}",
                        f"Bases URL configuradas: {bases if bases else 'nenhuma'}",
                        "Dica: configure IMAGE_BASE_URL no Streamlit Cloud se as imagens estiverem fora da pasta local.",
                    ]
                )
            )


def corrigir_mojibake(texto: str) -> str:
    saida = texto
    for _ in range(3):
        antes = saida
        for quebrado, correto in MOJIBAKE_MAP.items():
            saida = saida.replace(quebrado, correto)
        if saida == antes:
            break
    return saida


def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    normalizado = str(texto).strip()
    if "?" in normalizado or "?" in normalizado:
        normalizado = corrigir_mojibake(normalizado)
    normalizado = re.sub(r"\s+", " ", normalizado).strip()
    return normalizado


def extrair_json_de_js_slides(conteudo_js: str) -> str:
    bruto = str(conteudo_js or "").strip()
    if not bruto:
        return ""
    if bruto.startswith("["):
        return bruto

    match = re.search(r"window\.SLIDES_DATA\s*=\s*(\[.*\])\s*;?\s*$", bruto, flags=re.S)
    if match:
        return match.group(1)

    ini = bruto.find("[")
    fim = bruto.rfind("]")
    if ini >= 0 and fim > ini:
        return bruto[ini : fim + 1]
    return ""


def normalizar_slides(conteudo: list[dict]) -> list[dict]:
    slides: list[dict] = []
    for slide in conteudo:
        if not isinstance(slide, dict):
            continue
        titulo = normalizar_texto(str(slide.get("title", "")))
        textos_brutos = slide.get("texts", [])
        if not isinstance(textos_brutos, list):
            textos_brutos = []
        textos = [normalizar_texto(str(item)) for item in textos_brutos]
        textos = [item for item in textos if item and item != titulo]
        imagens = slide.get("images", [])
        if not isinstance(imagens, list):
            imagens = []
        slides.append(
            {
                "slide": int(slide.get("slide", 0) or 0),
                "title": titulo,
                "texts": textos,
                "images": [str(img) for img in imagens if str(img).strip()],
            }
        )
    return slides


@st.cache_data(show_spinner=False, ttl=1800)
def baixar_texto_url(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=6) as resposta:
            return resposta.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, OSError, ValueError):
        return ""


def listar_urls_slides_remotos() -> list[str]:
    urls: list[str] = []
    bases = listar_bases_url_imagem()
    for base in bases:
        base_norm = normalizar_base_url(base)
        if not base_norm:
            continue
        candidatos_base = [base_norm]
        if "/assets/images" in base_norm:
            candidatos_base.insert(0, base_norm.split("/assets/images", 1)[0])
        for raiz in candidatos_base:
            urls.append(f"{raiz}/data/slides.json")
            urls.append(f"{raiz}/data/slides-data.js")

    urls_unicas: list[str] = []
    vistos: set[str] = set()
    for url in urls:
        if url not in vistos:
            vistos.add(url)
            urls_unicas.append(url)
    return urls_unicas


def gerar_slides_fallback_por_imagens() -> list[dict]:
    mapa_legendas: dict[str, str] = {}
    for imagens_secao in IMAGENS_SECOES.values():
        for nome, legenda in imagens_secao:
            if nome not in mapa_legendas:
                mapa_legendas[nome] = legenda

    mapa_arquivos = indexar_arquivos_imagem()
    padrao = re.compile(r"^image(\d+)\.(png|jpg|jpeg|webp|gif|bmp)$", re.I)
    nomes = [nome for nome in mapa_arquivos.keys() if padrao.match(nome)]
    if not nomes:
        return []

    def chave_ordenacao(nome: str) -> tuple[int, str]:
        match = padrao.match(nome)
        numero = int(match.group(1)) if match else 10**9
        return (numero, nome)

    nomes.sort(key=chave_ordenacao)
    slides: list[dict] = []
    for idx, nome in enumerate(nomes, start=1):
        titulo = mapa_legendas.get(nome, f"Slide {idx}")
        slides.append(
            {
                "slide": idx,
                "title": normalizar_texto(titulo),
                "texts": [f"Imagem de apoio: {nome}"],
                "images": [nome],
            }
        )
    return slides


@st.cache_data(show_spinner=False, ttl=600)
def carregar_slides() -> list[dict]:
    fontes_locais: list[tuple[str, str]] = []
    slides_json_file = DATA_DIR / "slides.json"
    slides_js_file = DATA_DIR / "slides-data.js"

    if slides_json_file.exists():
        try:
            fontes_locais.append(("json", slides_json_file.read_text(encoding="utf-8")))
        except OSError:
            pass
    if slides_js_file.exists():
        try:
            fontes_locais.append(("js", slides_js_file.read_text(encoding="utf-8")))
        except OSError:
            pass

    for tipo, conteudo_texto in fontes_locais:
        try:
            if tipo == "json":
                conteudo = json.loads(conteudo_texto)
            else:
                payload = extrair_json_de_js_slides(conteudo_texto)
                conteudo = json.loads(payload) if payload else []
        except json.JSONDecodeError:
            continue
        if isinstance(conteudo, list):
            slides = normalizar_slides(conteudo)
            if slides:
                return slides

    for url in listar_urls_slides_remotos():
        conteudo_texto = baixar_texto_url(url)
        if not conteudo_texto:
            continue
        try:
            if url.lower().endswith(".json"):
                conteudo = json.loads(conteudo_texto)
            else:
                payload = extrair_json_de_js_slides(conteudo_texto)
                conteudo = json.loads(payload) if payload else []
        except json.JSONDecodeError:
            continue
        if isinstance(conteudo, list):
            slides = normalizar_slides(conteudo)
            if slides:
                return slides

    return gerar_slides_fallback_por_imagens()


def exibir_tratamento() -> None:
    exibir_titulo_secao(
        "Fluxo de Tratamento e Destinação",
        "Procedimento técnico com rastreabilidade e conformidade documental (MTR/CDF).",
    )
    exibir_mosaico_imagens("tratamento")
    for idx, etapa in enumerate(FLUXO_TRATAMENTO, start=1):
        st.markdown(
            f"""
            <div class="timeline-step">
                <strong>Etapa {idx}: {etapa["etapa"]}</strong>
                <p>{etapa["detalhe"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def exibir_planos_acao() -> None:
    exibir_titulo_secao(
        "Planos de Ação de Passivos",
        "Planos estruturados para erosão hídrica (PRAD) e vazamento de óleo.",
    )
    exibir_mosaico_imagens("planos")
    col1, col2 = st.columns(2)
    for idx, plano in enumerate(PLANOS_ACAO):
        destino_col = col1 if idx % 2 == 0 else col2
        with destino_col:
            itens_html = "".join(f"<li>{item}</li>" for item in plano["itens"])
            st.markdown(
                f"""
                <div class="plano-card">
                    <h3>{plano["titulo"]}</h3>
                    <div class="subtle" style="font-size:0.86rem;">{plano["subtitulo"]}</div>
                    <ul>{itens_html}</ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### Cronograma Integrado dos Passivos")
    cronograma_df = pd.DataFrame(CRONOGRAMA_PASSIVOS).copy()
    cronograma_df["inicio"] = pd.to_datetime(cronograma_df["inicio"], errors="coerce")
    cronograma_df["fim"] = pd.to_datetime(cronograma_df["fim"], errors="coerce")
    cronograma_df["prazo_dias"] = pd.to_numeric(cronograma_df["prazo_dias"], errors="coerce").fillna(0).astype(int)
    ordem_fases = [
        "Diagnóstico",
        "Contenção imediata",
        "Execução corretiva",
        "Recuperação ambiental / PRAD",
        "Monitoramento",
    ]
    cronograma_df["fase"] = pd.Categorical(cronograma_df["fase"], categories=ordem_fases, ordered=True)
    cronograma_df = cronograma_df.sort_values(["passivo", "fase", "inicio"]).reset_index(drop=True)

    tabela_df = cronograma_df.copy()
    tabela_df["prazo_sugerido"] = (
        tabela_df["inicio"].dt.strftime("%d/%m/%Y") + " a " + tabela_df["fim"].dt.strftime("%d/%m/%Y")
    )
    tabela_df = tabela_df.rename(
        columns={
            "passivo": "Passivo ambiental",
            "fase": "Fase",
            "acao_principal": "Ação principal",
            "objetivo_tecnico": "Objetivo técnico",
            "prazo_sugerido": "Prazo sugerido",
            "prioridade": "Prioridade",
            "status": "Status",
            "responsavel": "Responsável sugerido",
            "prazo_dias": "Prazo (dias)",
        }
    )
    st.dataframe(
        tabela_df[
            [
                "Passivo ambiental",
                "Fase",
                "Ação principal",
                "Objetivo técnico",
                "Prazo sugerido",
                "Prazo (dias)",
                "Prioridade",
                "Status",
                "Responsável sugerido",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

    mapa_cores_passivos = {"Erosão / voçoroca": "#3b82f6", "Vazamento de óleo": "#ef4444"}
    fig_crono = px.bar(
        cronograma_df,
        x="fase",
        y="prazo_dias",
        color="passivo",
        barmode="group",
        text="prazo_dias",
        category_orders={"fase": ordem_fases},
        color_discrete_map=mapa_cores_passivos,
        labels={"fase": "Fase", "prazo_dias": "Prazo (dias)", "passivo": "Passivo ambiental"},
        title="Plano de Ação / Cronograma de Passivos Ambientais",
    )
    fig_crono.update_traces(textposition="outside", cliponaxis=False)
    fig_crono.update_layout(
        height=470,
        xaxis_title="",
        yaxis_title="Prazo (dias)",
        legend_title_text="Passivo ambiental",
        margin=dict(t=70, l=20, r=20, b=20),
    )
    st.plotly_chart(fig_crono, width="stretch")

    monitoramento_df = cronograma_df[cronograma_df["fase"] == "Monitoramento"][["passivo", "prazo_dias"]].copy()
    if monitoramento_df.empty:
        monitoramento_df = cronograma_df.groupby("passivo", as_index=False)["prazo_dias"].sum()
    fig_prazo = px.pie(
        monitoramento_df,
        names="passivo",
        values="prazo_dias",
        color="passivo",
        color_discrete_map=mapa_cores_passivos,
        title="Prazo de Execução (foco em monitoramento)",
    )
    fig_prazo.update_traces(textposition="outside", textinfo="label+percent+value")
    fig_prazo.update_layout(height=420, margin=dict(t=70, l=20, r=20, b=20))
    st.plotly_chart(fig_prazo, width="stretch")


def exibir_galeria() -> None:
    exibir_titulo_secao(
        "Galeria Técnica da Apresentação",
        "Slides e fotos originais utilizados como base de consulta operacional.",
    )
    termo = st.text_input(
        "Buscar por tema",
        placeholder="água, resíduos, carbono, licenciamento...",
    ).strip().lower()
    imagens_locais = carregar_imagens_locais_cache()
    slides = carregar_slides()
    if not slides:
        st.warning("Nenhum slide encontrado. Verifique `data/slides.json` ou `data/slides-data.js` no deploy.")
        with st.expander("Diagnóstico da galeria", expanded=False):
            st.code(
                "\n".join(
                    [
                        f"DATA_DIR: {DATA_DIR}",
                        f"slides.json existe: {(DATA_DIR / 'slides.json').exists()}",
                        f"slides-data.js existe: {(DATA_DIR / 'slides-data.js').exists()}",
                        f"URLs remotas testadas: {listar_urls_slides_remotos()}",
                    ]
                )
            )
        return

    filtrados = []
    for slide in slides:
        imagens_texto = " ".join([extrair_nome_arquivo_imagem(str(img)) for img in slide.get("images", [])])
        texto_composto = f"{slide['title']} {' '.join(slide['texts'])} {imagens_texto}".lower()
        if not termo or termo in texto_composto:
            filtrados.append(slide)

    if not filtrados:
        st.info("Nenhum slide encontrado para essa busca.")
        return

    alguma_imagem_carregada = False
    imagens_exibidas: set[str] = set()
    for i in range(0, len(filtrados), 2):
        linha = filtrados[i : i + 2]
        colunas = st.columns(len(linha))
        for col, slide in zip(colunas, linha):
            with col:
                st.markdown(f"**Slide {slide['slide']}: {slide['title'] or 'Sem título'}**")
                if slide["images"]:
                    imagens_carregadas_slide = 0
                    for imagem in slide["images"]:
                        nome_base = extrair_nome_arquivo_imagem(str(imagem)).lower()
                        if exibir_imagem_por_nome(str(imagem)):
                            alguma_imagem_carregada = True
                            imagens_carregadas_slide += 1
                            if nome_base:
                                imagens_exibidas.add(nome_base)
                    if imagens_carregadas_slide == 0:
                        st.caption("Imagem não encontrada para este slide no deploy.")
                with st.expander("Ver pontos do slide"):
                    if slide["texts"]:
                        for item in slide["texts"][:8]:
                            st.write(f"- {item}")
                    else:
                        st.write("Conteúdo textual não identificado.")

    # Garante que todas as imagens locais também apareçam na galeria, mesmo se não vierem do JSON.
    if not termo and imagens_locais:
        nomes_restantes = [nome for nome in ordenar_nomes_imagem(list(imagens_locais.keys())) if nome not in imagens_exibidas]
        nomes_restantes = [
            nome
            for nome in nomes_restantes
            if nome.lower().startswith("pres_slide") or nome.lower().startswith("slide_")
        ]
        if nomes_restantes:
            st.markdown("### Imagens adicionais")
            st.caption("Arquivos locais detectados que não estavam vinculados aos slides de descrição.")
            for i in range(0, len(nomes_restantes), 3):
                grupo = nomes_restantes[i : i + 3]
                colunas = st.columns(len(grupo))
                for col, nome in zip(colunas, grupo):
                    with col:
                        exibir_imagem_segura(imagens_locais[nome], f"{nome} (sem descrição no slide)")
                        alguma_imagem_carregada = True

    if not alguma_imagem_carregada:
        st.info("A galeria não encontrou imagens disponíveis para renderização.")
        with st.expander("Diagnóstico de imagens da galeria", expanded=False):
            bases = listar_bases_url_imagem()
            host = host_execucao()
            bases_inferidas = inferir_bases_url_streamlit_cloud()
            st.code(
                "\n".join(
                    [
                        f"Host da sessão: {host or 'indisponível'}",
                        f"IMAGES_DIR esperado: {IMAGES_DIR}",
                        f"Imagens carregadas em cache local: {len(imagens_locais)}",
                        f"Arquivos de imagem detectados localmente: {len(indexar_arquivos_imagem())}",
                        f"Bases inferidas via URL do Streamlit: {bases_inferidas if bases_inferidas else 'nenhuma'}",
                        f"Bases URL configuradas: {bases if bases else 'nenhuma'}",
                    ]
                )
            )


def gerar_relatorio_prad_texto(
    empresa: str,
    empreendimento: str,
    localizacao: str,
    responsavel: str,
    data_vistoria: date,
    area_total_ha: float,
    area_recuperacao_ha: float,
    cobertura_vegetal_pct: float,
    meta_sobrevivencia_pct: float,
    prazo_meses: int,
    diagnostico_itens: list[str],
    metas_itens: list[str],
    observacoes: str,
    acoes_df: pd.DataFrame,
    df_residuos: pd.DataFrame,
) -> str:
    percentual_recuperacao = (area_recuperacao_ha / area_total_ha * 100) if area_total_ha > 0 else 0.0

    acoes_linhas: list[str] = []
    for _, linha in acoes_df.fillna("").iterrows():
        acao = str(linha.get("Ação", "")).strip()
        if not acao:
            continue
        responsavel_acao = str(linha.get("Responsável", "")).strip() or "Não definido"
        prioridade = str(linha.get("Prioridade", "")).strip() or "Não definida"
        status = str(linha.get("Status", "")).strip() or "Não iniciado"
        acoes_linhas.append(
            f"{len(acoes_linhas) + 1}. {acao} | Responsável: {responsavel_acao} | "
            f"Prioridade: {prioridade} | Status: {status}"
        )
    if not acoes_linhas:
        acoes_linhas = ["1. Definir ações executivas de recuperação."]

    if df_residuos.empty:
        resumo_residuos = "- Sem registros de resíduos para correlação com o monitoramento ambiental."
    else:
        total_registros = len(df_residuos)
        volume_total_kg = float(df_residuos["quantidade"].sum())
        taxa_destinado = float((df_residuos["status"] == "Destinado").mean() * 100)
        data_ref = formatar_data_br(df_residuos["data"].max())
        resumo_residuos = (
            f"- Registros avaliados: {total_registros}\n"
            f"- Volume total de resíduos monitorados: {formatar_numero_br(volume_total_kg, 1)} kg\n"
            f"- Taxa de destinação concluída: {formatar_numero_br(taxa_destinado, 1)}%\n"
            f"- Data de referência da base operacional: {data_ref}"
        )

    linhas = [
        "# Relatório de Recuperação de Área Degradada (PRAD)",
        "",
        f"Data de emissão: {date.today().strftime('%d/%m/%Y')}",
        "",
        "## 1. Identificação do Empreendimento",
        f"- Empresa: {empresa or 'Não informada'}",
        f"- Empreendimento: {empreendimento or 'Não informado'}",
        f"- Localização: {localizacao or 'Não informada'}",
        f"- Responsável técnico: {responsavel or 'Não informado'}",
        f"- Data da vistoria técnica: {data_vistoria.strftime('%d/%m/%Y')}",
        "",
        "## 2. Diagnóstico Ambiental",
        *[f"- {item}" for item in diagnostico_itens],
        "",
        "## 3. Objetivos e Metas de Recuperação",
        f"- Área total degradada: {formatar_numero_br(area_total_ha, 2)} ha",
        f"- Área em recuperação: {formatar_numero_br(area_recuperacao_ha, 2)} ha",
        f"- Percentual de recuperação atual: {formatar_numero_br(percentual_recuperacao, 1)}%",
        f"- Cobertura vegetal atual: {formatar_numero_br(cobertura_vegetal_pct, 1)}%",
        f"- Meta de sobrevivência de mudas: >= {formatar_numero_br(meta_sobrevivencia_pct, 1)}%",
        f"- Prazo previsto para execução: {prazo_meses} meses",
        *[f"- {item}" for item in metas_itens],
        "",
        "## 4. Plano de Ação",
        *acoes_linhas,
        "",
        "## 5. Integração com Monitoramento Operacional",
        resumo_residuos,
        "",
        "## 6. Observações Técnicas",
        observacoes.strip() if observacoes.strip() else "Sem observações adicionais.",
        "",
        "## 7. Conclusão",
        (
            "Este PRAD deve ser executado conforme as prioridades estabelecidas e revisado "
            "periodicamente para validação de desempenho ambiental."
        ),
    ]

    return "\n".join(linhas)


def gerar_relatorio_prad_xlsx(
    empresa: str,
    empreendimento: str,
    localizacao: str,
    responsavel: str,
    data_vistoria: date,
    area_total_ha: float,
    area_recuperacao_ha: float,
    cobertura_vegetal_pct: float,
    meta_sobrevivencia_pct: float,
    prazo_meses: int,
    diagnostico_itens: list[str],
    metas_itens: list[str],
    observacoes: str,
    acoes_df: pd.DataFrame,
    df_residuos: pd.DataFrame,
) -> bytes:
    percentual_recuperacao = (area_recuperacao_ha / area_total_ha * 100) if area_total_ha > 0 else 0.0

    resumo_df = pd.DataFrame(
        [
            {"Campo": "Data de emissao", "Valor": date.today().strftime("%d/%m/%Y")},
            {"Campo": "Empresa", "Valor": empresa or "Nao informada"},
            {"Campo": "Empreendimento", "Valor": empreendimento or "Nao informado"},
            {"Campo": "Localizacao", "Valor": localizacao or "Nao informada"},
            {"Campo": "Responsavel tecnico", "Valor": responsavel or "Nao informado"},
            {"Campo": "Data da vistoria", "Valor": data_vistoria.strftime("%d/%m/%Y")},
            {"Campo": "Area total degradada (ha)", "Valor": area_total_ha},
            {"Campo": "Area em recuperacao (ha)", "Valor": area_recuperacao_ha},
            {"Campo": "Recuperacao atual (%)", "Valor": percentual_recuperacao},
            {"Campo": "Cobertura vegetal atual (%)", "Valor": cobertura_vegetal_pct},
            {"Campo": "Meta de sobrevivencia (%)", "Valor": meta_sobrevivencia_pct},
            {"Campo": "Prazo de execucao (meses)", "Valor": prazo_meses},
            {
                "Campo": "Observacoes tecnicas",
                "Valor": observacoes.strip() if observacoes.strip() else "Sem observacoes adicionais.",
            },
        ]
    )

    diagnostico_df = pd.DataFrame(
        {"Diagnostico tecnico": diagnostico_itens if diagnostico_itens else ["Sem itens informados."]}
    )
    metas_df = pd.DataFrame({"Objetivos e metas": metas_itens if metas_itens else ["Sem metas informadas."]})

    plano_export_df = acoes_df.copy()
    colunas_plano = ["Ação", "Responsável", "Prioridade", "Status"]
    if plano_export_df.empty:
        plano_export_df = pd.DataFrame(
            [
                {
                    "Ação": "Definir ações executivas de recuperação.",
                    "Responsável": "Não definido",
                    "Prioridade": "Não definida",
                    "Status": "Não iniciado",
                }
            ]
        )
    else:
        for coluna in colunas_plano:
            if coluna not in plano_export_df.columns:
                plano_export_df[coluna] = ""
        plano_export_df = plano_export_df[colunas_plano].fillna("")
        for coluna in colunas_plano:
            plano_export_df[coluna] = plano_export_df[coluna].astype(str).str.strip()
        plano_export_df = plano_export_df.loc[plano_export_df["Ação"].ne("")].copy()
        plano_export_df["Responsável"] = plano_export_df["Responsável"].replace("", "Não definido")
        plano_export_df["Prioridade"] = plano_export_df["Prioridade"].replace("", "Não definida")
        plano_export_df["Status"] = plano_export_df["Status"].replace("", "Não iniciado")
        if plano_export_df.empty:
            plano_export_df = pd.DataFrame(
                [
                    {
                        "Ação": "Definir ações executivas de recuperação.",
                        "Responsável": "Não definido",
                        "Prioridade": "Não definida",
                        "Status": "Não iniciado",
                    }
                ]
            )

    if df_residuos.empty:
        resumo_residuos_df = pd.DataFrame(
            [
                {
                    "Indicador": "Situação",
                    "Valor": "Sem registros de resíduos para correlação com o monitoramento ambiental.",
                }
            ]
        )
        residuos_export_df = pd.DataFrame(
            [{"Mensagem": "Sem registros de resíduos para exportação nesta emissão do PRAD."}]
        )
    else:
        total_registros = len(df_residuos)
        volume_total_kg = float(df_residuos["quantidade"].sum())
        taxa_destinado = float((df_residuos["status"] == "Destinado").mean() * 100)
        data_ref = formatar_data_br(df_residuos["data"].max())
        resumo_residuos_df = pd.DataFrame(
            [
                {"Indicador": "Registros avaliados", "Valor": total_registros},
                {"Indicador": "Volume total monitorado (kg)", "Valor": volume_total_kg},
                {"Indicador": "Taxa de destinação concluída (%)", "Valor": taxa_destinado},
                {"Indicador": "Data de referência operacional", "Valor": data_ref},
            ]
        )

        residuos_export_df = df_residuos.copy()
        colunas_residuos = ["data", "tipo", "classe", "origem", "quantidade", "destino", "status"]
        for coluna in colunas_residuos:
            if coluna not in residuos_export_df.columns:
                residuos_export_df[coluna] = ""
        residuos_export_df = residuos_export_df[colunas_residuos]
        residuos_export_df["quantidade"] = pd.to_numeric(residuos_export_df["quantidade"], errors="coerce").fillna(0.0)
        data_series = pd.to_datetime(residuos_export_df["data"], errors="coerce")
        residuos_export_df["data"] = data_series.dt.strftime("%d/%m/%Y")
        residuos_export_df["data"] = residuos_export_df["data"].fillna("")
        residuos_export_df = residuos_export_df.rename(
            columns={
                "data": "Data",
                "tipo": "Tipo",
                "classe": "Classe",
                "origem": "Origem",
                "quantidade": "Quantidade (kg)",
                "destino": "Destino",
                "status": "Status",
            }
        )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        resumo_df.to_excel(writer, index=False, sheet_name="Resumo PRAD")
        diagnostico_df.to_excel(writer, index=False, sheet_name="Diagnostico")
        metas_df.to_excel(writer, index=False, sheet_name="Metas")
        plano_export_df.to_excel(writer, index=False, sheet_name="Plano de Acao")
        resumo_residuos_df.to_excel(writer, index=False, sheet_name="Resumo Residuos")
        residuos_export_df.to_excel(writer, index=False, sheet_name="Base Residuos")

    return output.getvalue()


def obter_registro_por_id(registros: list[dict], registro_id: str | None) -> dict | None:
    if not registro_id:
        return None
    for registro in registros:
        if registro.get("id") == registro_id:
            return registro
    return None


def exibir_dashboard(df: pd.DataFrame, tema: str) -> None:
    exibir_titulo_secao(
        "Dashboard Ambiental",
        "Indicadores da apresentação + dados operacionais cadastrados no aplicativo.",
    )
    exibir_mosaico_imagens("dashboard")
    exibir_lista_tipos_residuos("Dashboard", expanded=False)

    if df.empty:
        st.info("Sem registros para gerar indicadores. Cadastre ao menos um resíduo.")
        return

    total_registros = len(df)
    total_kg = float(df["quantidade"].sum())
    media_kg = float(df["quantidade"].mean())
    destinado_pct = float((df["status"] == "Destinado").mean() * 100)

    kpis_dinamicos = [
        ("Total de registros", f"{total_registros}", "Base operacional atual"),
        ("Taxa de destinação", f"{formatar_numero_br(destinado_pct, 1)}%", "Registros com status Destinado"),
    ]
    cards_kpi = KPIS_BASE + kpis_dinamicos
    for i in range(0, len(cards_kpi), 3):
        linha = cards_kpi[i : i + 3]
        colunas = st.columns(len(linha))
        for col, (titulo, valor, meta) in zip(colunas, linha):
            with col:
                st.markdown(
                    f"""
                    <div class="app-card">
                        <div style="font-size:0.85rem;opacity:0.85;">{titulo}</div>
                        <div style="font-size:1.5rem;font-weight:700;line-height:1.3;">{valor}</div>
                        <div style="font-size:0.8rem;opacity:0.75;">{meta}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown(
        """
        <style>
            .st-key-dashboard_metricas div[data-testid="stMetricLabel"] p,
            .st-key-dashboard_metricas div[data-testid="stMetricValue"] > div,
            .st-key-dashboard_metricas div[data-testid="stMetricDelta"] > div {
                color: var(--ink) !important;
                opacity: 1 !important;
            }
            .st-key-dashboard_metricas div[data-testid="stMetricDelta"] svg {
                fill: var(--ink) !important;
                stroke: var(--ink) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="dashboard_metricas"):
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Registros", f"{total_registros}")
        k2.metric("Volume total", f"{formatar_numero_br(total_kg, 1)} kg")
        k3.metric("Média por registro", f"{formatar_numero_br(media_kg, 1)} kg")
        k4.metric("Taxa destinada", f"{formatar_numero_br(destinado_pct, 1)}%")
    st.markdown("#### Gráficos Coloridos com Percentuais")

    tipo_volume_df = (
        df.groupby("tipo", as_index=False)["quantidade"]
        .sum()
        .sort_values("quantidade", ascending=False)
    )
    tipo_registros_df = (
        df.groupby("tipo", as_index=False)
        .size()
        .rename(columns={"size": "registros"})
        .sort_values("registros", ascending=False)
    )
    status_df = (
        df.groupby("status", as_index=False)
        .size()
        .rename(columns={"size": "registros"})
        .sort_values("registros", ascending=False)
    )
    destino_df = (
        df.groupby("destino", as_index=False)["quantidade"]
        .sum()
        .sort_values("quantidade", ascending=False)
    )
    classe_df = (
        df.groupby("classe", as_index=False)["quantidade"]
        .sum()
        .sort_values("quantidade", ascending=False)
    )

    total_tipo_kg = float(tipo_volume_df["quantidade"].sum())
    if total_tipo_kg > 0:
        tipo_volume_df["percentual"] = (tipo_volume_df["quantidade"] / total_tipo_kg) * 100
    else:
        tipo_volume_df["percentual"] = 0.0
    total_status = int(status_df["registros"].sum())
    if total_status > 0:
        status_df["percentual"] = (status_df["registros"] / total_status) * 100
    else:
        status_df["percentual"] = 0.0
    total_destino_kg = float(destino_df["quantidade"].sum())
    if total_destino_kg > 0:
        destino_df["percentual"] = (destino_df["quantidade"] / total_destino_kg) * 100
    else:
        destino_df["percentual"] = 0.0
    total_classe_kg = float(classe_df["quantidade"].sum())
    if total_classe_kg > 0:
        classe_df["percentual"] = (classe_df["quantidade"] / total_classe_kg) * 100
    else:
        classe_df["percentual"] = 0.0

    paleta_tipos = [
        "#0ea5e9",
        "#22c55e",
        "#0284c7",
        "#16a34a",
        "#06b6d4",
        "#15803d",
        "#38bdf8",
        "#4ade80",
        "#0369a1",
        "#166534",
    ]
    mapa_cores_tipos = {
        tipo: paleta_tipos[idx % len(paleta_tipos)]
        for idx, tipo in enumerate(tipo_volume_df["tipo"].tolist())
    }
    mapa_cores_status = {
        "Destinado": "#22c55e",
        "Em transporte": "#0ea5e9",
        "Aguardando coleta": "#f59e0b",
        "Não conformidade": "#ef4444",
    }
    paleta_destino = ["#16a34a", "#0ea5e9", "#14b8a6", "#f59e0b", "#3b82f6", "#f97316"]
    mapa_cores_destino = {
        destino: paleta_destino[idx % len(paleta_destino)]
        for idx, destino in enumerate(destino_df["destino"].tolist())
    }
    paleta_classes = ["#06b6d4", "#22c55e", "#a855f7"]
    mapa_cores_classes = {
        classe: paleta_classes[idx % len(paleta_classes)]
        for idx, classe in enumerate(classe_df["classe"].tolist())
    }

    template_plotly = "plotly_dark" if tema == "dark" else "plotly_white"
    cor_texto_grafico = "#def4ea" if tema == "dark" else "#143327"

    st.markdown(
        """
        <style>
            .dashboard-legenda {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 6px;
                margin-top: 8px;
            }
            .dashboard-legenda-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 7px 9px;
                border-radius: 8px;
                background: rgba(14, 165, 233, 0.08);
                line-height: 1.2;
            }
            @media (max-width: 900px) {
                .dashboard-legenda {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    linha1_col1, linha1_col2 = st.columns(2)

    with linha1_col1:
        fig_tipos = px.pie(
            tipo_volume_df,
            names="tipo",
            values="quantidade",
            color="tipo",
            color_discrete_map=mapa_cores_tipos,
            hole=0.5,
            title="Percentual de Volume por Tipo",
        )
        fig_tipos.update_traces(
            textposition="inside",
            texttemplate="%{percent:.1%}",
            hovertemplate="%{label}<br>%{value:.1f} kg<br>%{percent:.1%}<extra></extra>",
            textfont=dict(color=cor_texto_grafico, size=13),
        )
        fig_tipos.update_layout(
            template=template_plotly,
            legend_title_text="Tipo de resíduo",
            height=460,
            margin=dict(l=0, r=0, t=48, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(
                    text=f"<b>{formatar_numero_br(total_tipo_kg, 0)} kg</b><br>Total",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=16, color=cor_texto_grafico),
                )
            ],
            font=dict(color=cor_texto_grafico),
        )
        st.plotly_chart(fig_tipos, width="stretch")

    with linha1_col2:
        fig_status = px.pie(
            status_df,
            names="status",
            values="registros",
            color="status",
            color_discrete_map=mapa_cores_status,
            hole=0.5,
            title="Percentual de Registros por Status",
        )
        fig_status.update_traces(
            textposition="inside",
            texttemplate="%{percent:.1%}",
            hovertemplate="%{label}<br>%{value:.0f} registros<br>%{percent:.1%}<extra></extra>",
            textfont=dict(color=cor_texto_grafico, size=13),
        )
        fig_status.update_layout(
            template=template_plotly,
            legend_title_text="Status",
            height=460,
            margin=dict(l=0, r=0, t=48, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=cor_texto_grafico),
        )
        st.plotly_chart(fig_status, width="stretch")

    linha2_col1, linha2_col2 = st.columns(2)

    with linha2_col1:
        destino_plot_df = destino_df.sort_values("percentual", ascending=True).copy()
        destino_plot_df["rotulo"] = destino_plot_df.apply(
            lambda linha: f"{linha['percentual']:.1f}% ({linha['quantidade']:.1f} kg)",
            axis=1,
        )
        fig_destino = px.bar(
            destino_plot_df,
            x="percentual",
            y="destino",
            orientation="h",
            color="destino",
            color_discrete_map=mapa_cores_destino,
            title="Destinação (% do Volume Total)",
        )
        fig_destino.update_layout(
            template=template_plotly,
            showlegend=False,
            xaxis_title="% do volume",
            yaxis_title="",
            xaxis_ticksuffix="%",
            height=440,
            margin=dict(l=0, r=0, t=48, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=cor_texto_grafico),
        )
        fig_destino.update_traces(
            text=destino_plot_df["rotulo"],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
            textfont=dict(color=cor_texto_grafico, size=12),
        )
        st.plotly_chart(fig_destino, width="stretch")

    with linha2_col2:
        classe_plot_df = classe_df.sort_values("percentual", ascending=False).copy()
        fig_classes = px.bar(
            classe_plot_df,
            x="classe",
            y="percentual",
            color="classe",
            color_discrete_map=mapa_cores_classes,
            title="Participação por Classe de Resíduo (%)",
            text=classe_plot_df["percentual"].map(lambda v: f"{v:.1f}%"),
        )
        fig_classes.update_layout(
            template=template_plotly,
            showlegend=False,
            xaxis_title="Classe",
            yaxis_title="Percentual",
            yaxis_ticksuffix="%",
            height=440,
            margin=dict(l=0, r=0, t=48, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=cor_texto_grafico),
        )
        fig_classes.update_traces(
            textposition="outside",
            cliponaxis=False,
            textfont=dict(color=cor_texto_grafico, size=12),
        )
        st.plotly_chart(fig_classes, width="stretch")

    resumo_pct_df = tipo_registros_df.copy()
    total_reg_tipo = float(resumo_pct_df["registros"].sum())
    if total_reg_tipo > 0:
        resumo_pct_df["percentual_registros"] = (resumo_pct_df["registros"] / total_reg_tipo) * 100
    else:
        resumo_pct_df["percentual_registros"] = 0.0
    resumo_pct_df = resumo_pct_df.rename(
        columns={
            "tipo": "Tipo de resíduo",
            "registros": "Registros",
            "percentual_registros": "Participação (%)",
        }
    )
    resumo_pct_df["Participação (%)"] = resumo_pct_df["Participação (%)"].map(lambda valor: f"{valor:.1f}%")
    st.markdown("#### Resumo Percentual por Tipo (Registros)")
    st.dataframe(resumo_pct_df, width="stretch", hide_index=True)

    linhas_legenda = []
    for _, linha in tipo_volume_df.iterrows():
        tipo_nome = str(linha["tipo"])
        cor = mapa_cores_tipos[tipo_nome]
        percentual = float(linha["percentual"])
        volume = float(linha["quantidade"])
        linhas_legenda.append(
            (
                "<div class='dashboard-legenda-item'>"
                f"<span style='display:inline-block;width:12px;height:12px;border-radius:999px;background:{cor};'></span>"
                f"<span style='font-size:0.9rem'>{tipo_nome}: <b>{percentual:.1f}%</b> ({volume:.1f} kg)</span>"
                "</div>"
            )
        )
    st.markdown(
        "<div class='dashboard-legenda'>"
        + "".join(linhas_legenda)
        + "</div>",
        unsafe_allow_html=True,
    )


def exibir_relatorio_prad(df_residuos: pd.DataFrame) -> None:
    exibir_titulo_secao(
        "Relatório de Recuperação de Área Degradada (PRAD)",
        "Diagnóstico, metas, cronograma e plano de ação para recuperação ambiental.",
    )
    exibir_mosaico_imagens("prad")

    df_metricas = df_residuos.copy()
    if df_metricas.empty:
        df_metricas = pd.DataFrame(columns=["tipo", "status", "destino", "quantidade"])
    if "quantidade" not in df_metricas.columns:
        df_metricas["quantidade"] = 0.0
    if "tipo" not in df_metricas.columns:
        df_metricas["tipo"] = ""
    if "status" not in df_metricas.columns:
        df_metricas["status"] = ""
    if "destino" not in df_metricas.columns:
        df_metricas["destino"] = ""

    df_metricas["quantidade"] = pd.to_numeric(df_metricas["quantidade"], errors="coerce").fillna(0.0)
    tipo_norm = df_metricas["tipo"].astype(str).map(normalizar_texto_comparacao)
    status_norm = df_metricas["status"].astype(str).map(normalizar_texto_comparacao)
    destino_norm = df_metricas["destino"].astype(str).map(normalizar_texto_comparacao)
    destinos_valorizacao_norm = {normalizar_texto_comparacao(item) for item in DESTINOS_VALORIZACAO}

    total_kg = float(df_metricas["quantidade"].sum())
    solo_contaminado_kg = float(df_metricas.loc[tipo_norm.str.contains("solo contaminado", na=False), "quantidade"].sum())
    nao_conformes = int(status_norm.eq("nao conformidade").sum())
    taxa_nao_conforme = (nao_conformes / len(df_metricas) * 100) if len(df_metricas) > 0 else 0.0
    kg_valorizado = float(df_metricas.loc[destino_norm.isin(destinos_valorizacao_norm), "quantidade"].sum())
    taxa_valorizacao = (kg_valorizado / total_kg * 100) if total_kg > 0 else 0.0

    area_total_ref = float(RELATORIO_PRAD.get("area_total_ha", 0.0) or 0.0)
    area_recuperacao_ref = float(RELATORIO_PRAD.get("area_recuperacao_ha", 0.0) or 0.0)
    recuperacao_ref_pct = (area_recuperacao_ref / area_total_ref * 100) if area_total_ref > 0 else 0.0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Área em recuperação", f"{formatar_numero_br(area_recuperacao_ref, 1)} ha")
    k2.metric("Solo contaminado monitorado", f"{formatar_numero_br(solo_contaminado_kg, 1)} kg")
    k3.metric("Não conformidades", f"{nao_conformes}")
    k4.metric("Valorização de resíduos", f"{formatar_numero_br(taxa_valorizacao, 1)}%")
    st.caption(
        f"Recuperação de referência: {formatar_numero_br(recuperacao_ref_pct, 1)}% | "
        f"Taxa de não conformidade: {formatar_numero_br(taxa_nao_conforme, 1)}%"
    )
    st.caption(
        f"Local de referência: {RELATORIO_RECUPERACAO['municipio']} | Data-base: {RELATORIO_RECUPERACAO['referencia']}"
    )

    d1, d2 = st.columns(2)
    with d1:
        st.markdown("**Diagnóstico técnico**")
        for item in RELATORIO_RECUPERACAO["diagnostico"]:
            st.write(f"- {item}")
    with d2:
        st.markdown("**Objetivos e metas**")
        for item in RELATORIO_RECUPERACAO["metas"]:
            st.write(f"- {item}")

    st.markdown("**Cronograma de recuperação**")
    cronograma_df = pd.DataFrame(RELATORIO_RECUPERACAO["cronograma"])
    cronograma_df = cronograma_df.rename(
        columns={
            "fase": "Fase",
            "periodo": "Período",
            "escopo": "Escopo",
            "entregavel": "Entregável",
        }
    )
    st.dataframe(cronograma_df, width="stretch", hide_index=True)

    st.markdown("**Plano de ação**")
    plano_df = pd.DataFrame(RELATORIO_RECUPERACAO["acoes"])
    plano_df = plano_df.rename(
        columns={
            "acao": "Ação",
            "responsavel": "Responsável",
            "prazo": "Prazo",
            "prioridade": "Prioridade",
            "status": "Status",
        }
    )
    st.dataframe(plano_df, width="stretch", hide_index=True)

    st.markdown("**Plano de monitoramento**")
    for item in RELATORIO_RECUPERACAO["monitoramento"]:
        st.write(f"- {item}")

    st.markdown("---")
    st.markdown("### Gerador do Relatório PRAD")
    st.caption("Preencha os campos para gerar e baixar o relatório PRAD atualizado.")

    i1, i2, i3 = st.columns(3)
    empresa = i1.text_input("Empresa", value=RELATORIO_PRAD["empresa"])
    empreendimento = i2.text_input("Empreendimento", value=RELATORIO_PRAD["empreendimento"])
    localizacao = i3.text_input("Localização", value=RELATORIO_PRAD["localizacao"])

    i4, i5, i6 = st.columns(3)
    responsavel = i4.text_input("Responsável técnico", value=RELATORIO_PRAD["responsavel"])
    data_vistoria = i5.date_input("Data da vistoria", value=date.today())
    prazo_meses = int(
        i6.number_input(
            "Prazo de execução (meses)",
            min_value=1,
            max_value=120,
            value=int(RELATORIO_PRAD["prazo_meses"]),
            step=1,
        )
    )

    c1, c2, c3, c4 = st.columns(4)
    area_total_ha = float(
        c1.number_input(
            "Área total degradada (ha)",
            min_value=0.0,
            value=float(RELATORIO_PRAD["area_total_ha"]),
            step=0.1,
        )
    )
    area_recuperacao_ha = float(
        c2.number_input(
            "Área em recuperação (ha)",
            min_value=0.0,
            value=float(RELATORIO_PRAD["area_recuperacao_ha"]),
            step=0.1,
        )
    )
    cobertura_vegetal_pct = float(
        c3.number_input(
            "Cobertura vegetal atual (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(RELATORIO_PRAD["cobertura_vegetal_pct"]),
            step=0.1,
        )
    )
    meta_sobrevivencia_pct = float(
        c4.number_input(
            "Meta de sobrevivência (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(RELATORIO_PRAD["meta_sobrevivencia_pct"]),
            step=0.1,
        )
    )

    if area_total_ha > 0 and area_recuperacao_ha > area_total_ha:
        st.warning("A área em recuperação está maior que a área total degradada. Revise os valores.")

    percentual_recuperacao = (area_recuperacao_ha / area_total_ha * 100) if area_total_ha > 0 else 0.0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Área total degradada", f"{formatar_numero_br(area_total_ha, 1)} ha")
    m2.metric("Área em recuperação", f"{formatar_numero_br(area_recuperacao_ha, 1)} ha")
    m3.metric("Recuperação atual", f"{formatar_numero_br(percentual_recuperacao, 1)}%")
    m4.metric("Cobertura vegetal", f"{formatar_numero_br(cobertura_vegetal_pct, 1)}%")

    d1, d2 = st.columns(2)
    diagnostico_texto = d1.text_area(
        "Diagnóstico técnico",
        value="\n".join(f"- {item}" for item in RELATORIO_PRAD["diagnostico"]),
        height=160,
    )
    metas_texto = d2.text_area(
        "Objetivos e metas",
        value="\n".join(f"- {item}" for item in RELATORIO_PRAD["metas"]),
        height=160,
    )

    st.markdown("**Plano de ação**")
    if "prad_acoes_df" not in st.session_state:
        st.session_state.prad_acoes_df = pd.DataFrame(
            RELATORIO_PRAD["acoes"],
            columns=["Ação", "Responsável", "Prioridade", "Status"],
        )

    if "Acao" in st.session_state.prad_acoes_df.columns:
        st.session_state.prad_acoes_df = st.session_state.prad_acoes_df.rename(columns={"Acao": "Ação"})
    if "Responsavel" in st.session_state.prad_acoes_df.columns:
        st.session_state.prad_acoes_df = st.session_state.prad_acoes_df.rename(
            columns={"Responsavel": "Responsável"}
        )

    acoes_df = st.data_editor(
        st.session_state.prad_acoes_df,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        key="prad_acoes_editor",
    )
    st.session_state.prad_acoes_df = acoes_df

    observacoes = st.text_area(
        "Observações técnicas complementares",
        value="Incluir evidências fotográficas, ART e cronograma executivo detalhado na versão final.",
        height=100,
    )

    diagnostico_itens = texto_para_itens(diagnostico_texto, RELATORIO_PRAD["diagnostico"])
    metas_itens = texto_para_itens(metas_texto, RELATORIO_PRAD["metas"])
    relatorio_kwargs = {
        "empresa": empresa,
        "empreendimento": empreendimento,
        "localizacao": localizacao,
        "responsavel": responsavel,
        "data_vistoria": data_vistoria,
        "area_total_ha": area_total_ha,
        "area_recuperacao_ha": area_recuperacao_ha,
        "cobertura_vegetal_pct": cobertura_vegetal_pct,
        "meta_sobrevivencia_pct": meta_sobrevivencia_pct,
        "prazo_meses": prazo_meses,
        "diagnostico_itens": diagnostico_itens,
        "metas_itens": metas_itens,
        "observacoes": observacoes,
        "acoes_df": acoes_df,
        "df_residuos": df_residuos,
    }
    relatorio_texto = gerar_relatorio_prad_texto(**relatorio_kwargs)

    relatorio_xlsx: bytes | None = None
    erro_xlsx = ""
    try:
        relatorio_xlsx = gerar_relatorio_prad_xlsx(**relatorio_kwargs)
    except Exception as exc:
        erro_xlsx = str(exc)

    st.markdown("**Prévia do relatório gerado**")
    st.text_area("Conteúdo PRAD", value=relatorio_texto, height=420, disabled=True)

    nome_base = f"PRAD_{slug_nome_arquivo(empreendimento or empresa)}_{date.today().isoformat()}"
    b1, b2, b3 = st.columns(3)
    b1.download_button(
        "Baixar relatório (.md)",
        data=relatorio_texto.encode("utf-8"),
        file_name=f"{nome_base}.md",
        mime="text/markdown",
        width="stretch",
    )
    b2.download_button(
        "Baixar relatório (.txt)",
        data=relatorio_texto.encode("utf-8"),
        file_name=f"{nome_base}.txt",
        mime="text/plain",
        width="stretch",
    )
    if relatorio_xlsx is not None:
        b3.download_button(
            "Baixar relatório (.xlsx)",
            data=relatorio_xlsx,
            file_name=f"{nome_base}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    else:
        b3.button("Baixar relatório (.xlsx)", width="stretch", disabled=True)
        st.warning(
            "Não foi possível gerar o arquivo .xlsx nesta execução. "
            f"Detalhe técnico: {erro_xlsx or 'erro não identificado'}"
        )


def main() -> None:
    st.set_page_config(page_title="Gestão de Resíduos", page_icon="♻️", layout="wide")

    if "tema" not in st.session_state:
        st.session_state.tema = "light"
    if "registros" not in st.session_state:
        st.session_state.registros = carregar_registros()
    if "editando_id" not in st.session_state:
        st.session_state.editando_id = None
    if "flash" not in st.session_state:
        st.session_state.flash = ""

    aplicar_tema_css(st.session_state.tema)
    st.markdown('<div id="topo-app"></div>', unsafe_allow_html=True)

    topo1, topo2 = st.columns([0.82, 0.18])
    with topo1:
        st.markdown("`Aplicativo Operacional`")
        st.title("Gestão de Resíduos Industriais")
        st.caption("Baseado na apresentação de Gestão Ambiental da Bracell.")
    with topo2:
        t1, t2 = st.columns(2)
        if t1.button("☀", width="stretch", help="Tema claro", key="theme_btn_light"):
            st.session_state.tema = "light"
            st.rerun()
        if t2.button("🌙", width="stretch", help="Tema escuro", key="theme_btn_dark"):
            st.session_state.tema = "dark"
            st.rerun()

    hero1, hero2 = st.columns([0.63, 0.37])
    with hero1:
        st.markdown(
            """
            <div class="hero-card">
                <h3>Visão Estratégica</h3>
                <p>
                    Plataforma para registrar, acompanhar e analisar a gestão de resíduos com base
                    nos indicadores e nas práticas ambientais da Bracell.
                </p>
                <div class="hero-badges">
                    <span>ISO 14001</span>
                    <span>PNRS 12.305/2010</span>
                    <span>Rastreabilidade MTR/CDF</span>
                    <span>Meta 2030: -90% aterro</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hero2:
        hero_img = resolver_caminho_imagem(HERO_IMAGE_FILE.name)
        if hero_img:
            if not exibir_imagem_segura(hero_img, "Foto de referência da operação Bracell"):
                st.warning("Falha ao carregar a imagem principal.")
        else:
            st.warning("Imagem da Bracell não encontrada em assets/images/apresentacao/pres_slide01.png.")

    if st.session_state.flash:
        st.success(st.session_state.flash)
        st.session_state.flash = ""

    abas = st.tabs(["Dashboard", "Resíduos", "Tratamento", "Planos de Ação", "Relatório PRAD", "Galeria"])

    with abas[1]:
        exibir_titulo_secao(
            "Controle de Resíduos",
            "Cadastro de geração, classe, volume e destinação dos resíduos industriais.",
        )
        exibir_mosaico_imagens("residuos")
        exibir_lista_tipos_residuos("Resíduos", expanded=True)

        editando = obter_registro_por_id(st.session_state.registros, st.session_state.editando_id)
        padrao_data = date.today()
        padrao_tipo = TIPOS_RESIDUO[0]
        padrao_classe = CLASSES_RESIDUO[0]
        padrao_origem = ""
        padrao_quantidade = 0.0
        padrao_destino = DESTINACOES[0]
        padrao_status = STATUS_REGISTRO[0]

        if editando:
            try:
                padrao_data = date.fromisoformat(str(editando.get("data", date.today().isoformat())))
            except ValueError:
                padrao_data = date.today()
            padrao_tipo = editando.get("tipo", padrao_tipo)
            padrao_classe = editando.get("classe", padrao_classe)
            padrao_origem = editando.get("origem", "")
            padrao_quantidade = float(editando.get("quantidade", 0.0))
            padrao_destino = editando.get("destino", padrao_destino)
            padrao_status = editando.get("status", padrao_status)
            st.info("Modo edição ativo. Atualize os campos e clique em salvar.")

        if padrao_classe not in CLASSES_RESIDUO:
            padrao_classe = CLASSE_POR_TIPO.get(padrao_tipo, CLASSES_RESIDUO[0])
        if padrao_tipo in CLASSE_POR_TIPO and padrao_tipo not in TIPOS_RESIDUO_POR_CLASSE.get(padrao_classe, []):
            padrao_classe = CLASSE_POR_TIPO[padrao_tipo]

        with st.form("form_residuos", clear_on_submit=False):
            f1, f2, f3 = st.columns(3)
            data_registro = f1.date_input("Data", value=padrao_data)
            classe = f2.selectbox(
                "Classe",
                CLASSES_RESIDUO,
                index=CLASSES_RESIDUO.index(padrao_classe) if padrao_classe in CLASSES_RESIDUO else 0,
            )
            tipos_disponiveis = TIPOS_RESIDUO_POR_CLASSE.get(classe, TIPOS_RESIDUO)
            tipo = f3.selectbox(
                "Tipo de resíduo",
                tipos_disponiveis,
                index=tipos_disponiveis.index(padrao_tipo) if padrao_tipo in tipos_disponiveis else 0,
            )

            f4, f5, f6 = st.columns(3)
            origem = f4.text_input("Origem / Setor", value=padrao_origem)
            quantidade = f5.number_input("Quantidade (kg)", min_value=0.0, value=padrao_quantidade, step=0.1)
            destino = f6.selectbox(
                "Destinação",
                DESTINACOES,
                index=DESTINACOES.index(padrao_destino) if padrao_destino in DESTINACOES else 0,
            )

            status = st.selectbox(
                "Status",
                STATUS_REGISTRO,
                index=STATUS_REGISTRO.index(padrao_status) if padrao_status in STATUS_REGISTRO else 0,
            )

            salvar = st.form_submit_button("Salvar registro", type="primary", width="stretch")

        if salvar:
            if not origem.strip():
                st.error("Preencha o campo de origem/setor antes de salvar.")
            else:
                novo_registro = {
                    "id": editando["id"] if editando else str(uuid.uuid4()),
                    "data": data_registro.isoformat(),
                    "tipo": tipo,
                    "classe": classe,
                    "origem": origem.strip(),
                    "quantidade": float(quantidade),
                    "destino": destino,
                    "status": status,
                }

                if editando:
                    atualizados = []
                    for registro in st.session_state.registros:
                        if registro.get("id") == editando["id"]:
                            atualizados.append(novo_registro)
                        else:
                            atualizados.append(registro)
                    st.session_state.registros = atualizados
                    st.session_state.editando_id = None
                    st.session_state.flash = "Registro atualizado com sucesso."
                else:
                    st.session_state.registros.append(novo_registro)
                    st.session_state.flash = "Registro salvo com sucesso."

                ok, erro = salvar_registros(st.session_state.registros)
                if not ok:
                    st.error(f"Registro salvo na sessão, mas não foi possível gravar em arquivo: {erro}")
                st.rerun()

        ac1, ac2 = st.columns([0.2, 0.8])
        if ac1.button("Cancelar edição", width="stretch", disabled=st.session_state.editando_id is None):
            st.session_state.editando_id = None
            st.rerun()

        st.markdown("---")
        st.markdown("### Registros cadastrados")

        df = registros_para_df(st.session_state.registros)

        p1, p2 = st.columns(2)
        termo_busca = p1.text_input("Buscar por tipo, origem ou destinação")
        filtro_status = p2.selectbox("Filtrar por status", ["Todos"] + STATUS_REGISTRO)

        if termo_busca.strip():
            termo = termo_busca.strip().lower()
            mascara = (
                df["tipo"].str.lower().str.contains(termo, na=False)
                | df["origem"].str.lower().str.contains(termo, na=False)
                | df["destino"].str.lower().str.contains(termo, na=False)
            )
            df = df[mascara]

        if filtro_status != "Todos":
            df = df[df["status"] == filtro_status]

        if df.empty:
            st.warning("Nenhum registro encontrado para os filtros aplicados.")
        else:
            tabela = df.copy()
            tabela["data"] = tabela["data"].apply(formatar_data_br)
            st.dataframe(
                tabela[["data", "tipo", "classe", "origem", "quantidade", "destino", "status"]],
                width="stretch",
                hide_index=True,
            )

            registros_opcoes = df["id"].tolist()
            selecionado = st.selectbox(
                "Selecionar registro para editar ou excluir",
                registros_opcoes,
                format_func=lambda rid: (
                    f"{formatar_data_br(df.loc[df['id'] == rid, 'data'].iloc[0])} | "
                    f"{df.loc[df['id'] == rid, 'tipo'].iloc[0]} | "
                    f"{df.loc[df['id'] == rid, 'origem'].iloc[0]}"
                ),
            )

            b1, b2 = st.columns(2)
            if b1.button("Editar selecionado", width="stretch"):
                st.session_state.editando_id = selecionado
                st.rerun()

            if b2.button("Excluir selecionado", width="stretch"):
                st.session_state.registros = [
                    item for item in st.session_state.registros if item.get("id") != selecionado
                ]
                ok, erro = salvar_registros(st.session_state.registros)
                if ok:
                    st.session_state.flash = "Registro excluído com sucesso."
                    st.session_state.editando_id = None
                    st.rerun()
                else:
                    st.error(f"Falha ao excluir em arquivo: {erro}")

    with abas[0]:
        exibir_dashboard(registros_para_df(st.session_state.registros), st.session_state.tema)

    with abas[2]:
        exibir_tratamento()

    with abas[3]:
        exibir_planos_acao()

    with abas[4]:
        exibir_relatorio_prad(registros_para_df(st.session_state.registros))

    with abas[5]:
        exibir_galeria()

    st.markdown("---")
    st.markdown("**Aviso Legal (Disclaimer)**")
    st.info(AVISO_LEGAL_DISCLAIMER)
    st.markdown(
        '<div class="back-top-wrap"><a class="back-top-link" href="#topo-app">⬆ Subir ao topo</a></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="footer-note">Aplicativo de Gestão de Resíduos | Engenharia & Sustentabilidade</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
