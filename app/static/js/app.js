/**
 * Market Price Tracker - Frontend Logic (Tailwind Version)
 *
 * Reestruturado para o novo schema:
 *   - Produto usa tipo/subtipo em vez de nome
 *   - Embalagem (conteudo_embalagem, unidade_medida) mora no Produto
 *   - Compra ganha nfe e observacoes
 *   - CompraItem simplificado (sem peso_vol_total/unidade_medida)
 */

const API_BASE = window.location.origin;

// =========================================================================
// API SERVICES
// =========================================================================

async function fetchCompras() {
    try {
        const response = await fetch(`${API_BASE}/compras/`);
        if (!response.ok) throw new Error('Falha ao buscar compras');
        return await response.json();
    } catch (error) {
        console.error(error);
        return [];
    }
}

async function fetchProdutos() {
    try {
        const response = await fetch(`${API_BASE}/produtos/`);
        if (!response.ok) throw new Error('Falha ao buscar produtos');
        return await response.json();
    } catch (error) {
        console.error(error);
        return [];
    }
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
}

/**
 * Monta o nome de exibição de um produto a partir de tipo/subtipo/marca.
 */
function produtoDisplayName(produto) {
    let label = produto.tipo;
    if (produto.subtipo) label += ` ${produto.subtipo}`;
    label += ` — ${produto.marca}`;
    label += ` (${produto.conteudo_embalagem}${produto.unidade_medida})`;
    return label;
}

// Configurações Globais do Chart.js para Dark Mode Tailwind
if (typeof Chart !== 'undefined') {
    Chart.defaults.color = '#94a3b8'; // text-slate-400
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.scale.grid.color = 'rgba(255, 255, 255, 0.05)';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)'; // bg-slate-900
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
}

// =========================================================================
// DASHBOARD DE PREÇOS (Nova Versão)
// =========================================================================

async function fetchCestas() {
    try {
        const response = await fetch(`${API_BASE}/api/dashboard/cestas`);
        if (!response.ok) throw new Error('Falha ao buscar cestas');
        return await response.json();
    } catch (error) {
        console.error(error);
        return { cesta_simples: [], cesta_completa: [] };
    }
}

async function fetchSearch(query) {
    try {
        const response = await fetch(`${API_BASE}/api/dashboard/search?query=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Falha ao buscar produto');
        return await response.json();
    } catch (error) {
        console.error(error);
        return { resultados: [] };
    }
}

async function initDashboard() {
    const inputSearch = document.getElementById('input-search');
    const searchResults = document.getElementById('search-results');
    const searchList = document.getElementById('search-list');
    
    const cestasGrid = document.getElementById('cestas-grid');
    const tabSimples = document.getElementById('tab-simples');
    const tabCompleta = document.getElementById('tab-completa');
    
    if (!inputSearch) return; // Não está na página do dashboard

    // 1. Carrega as Cestas Iniciais
    const cestasData = await fetchCestas();
    let currentTab = 'simples';

    function renderCestas() {
        if (!cestasGrid) return;
        cestasGrid.innerHTML = '';
        
        const data = currentTab === 'simples' ? cestasData.cesta_simples : cestasData.cesta_completa;
        
        if (data.length === 0) {
            cestasGrid.innerHTML = '<p class="text-slate-400">Nenhum dado suficiente para formar cestas.</p>';
            return;
        }

        data.forEach((item, index) => {
            // Se for o primeiro (mais barato) e tiver status Completa, ganha coroa
            const isWinner = index === 0 && item.status === 'Completa';
            const statusClass = item.status === 'Completa' ? 'text-neon-green' : 'text-amber-400';
            
            let missingHtml = '';
            if (item.faltantes.length > 0) {
                missingHtml = `<div class="mt-3 pt-3 border-t border-slate-700/50 text-xs text-slate-400">
                    <span class="text-amber-400"><i class="fa-solid fa-circle-exclamation"></i> Faltam dados:</span> ${item.faltantes.join(', ')}
                </div>`;
            }

            const card = `
                <div class="glass-panel p-6 rounded-2xl relative overflow-hidden border ${isWinner ? 'border-neon-green shadow-[0_0_15px_rgba(34,197,94,0.2)]' : 'border-slate-700/50'}">
                    ${isWinner ? '<div class="absolute -right-6 -top-6 text-5xl opacity-10">👑</div>' : ''}
                    <h3 class="text-lg font-bold text-slate-200 mb-1 flex items-center gap-2">
                        ${isWinner ? '<i class="fa-solid fa-crown text-neon-green"></i>' : '<i class="fa-solid fa-store text-slate-500"></i>'}
                        ${item.mercado}
                    </h3>
                    <div class="flex items-end gap-2 mb-2">
                        <span class="text-3xl font-black text-white">${formatCurrency(item.preco_total)}</span>
                        <span class="text-sm pb-1 text-slate-400">/ un. padrão</span>
                    </div>
                    <div class="text-sm font-medium ${statusClass}">
                        ${item.status}
                    </div>
                    ${missingHtml}
                </div>
            `;
            cestasGrid.innerHTML += card;
        });
    }

    renderCestas();

    // Tabs Control
    if (tabSimples && tabCompleta) {
        tabSimples.addEventListener('click', () => {
            currentTab = 'simples';
            tabSimples.className = 'px-4 py-1.5 rounded text-sm font-medium transition-colors bg-neon-purple text-white shadow';
            tabCompleta.className = 'px-4 py-1.5 rounded text-sm font-medium text-slate-400 hover:text-white transition-colors';
            renderCestas();
        });
        
        tabCompleta.addEventListener('click', () => {
            currentTab = 'completa';
            tabCompleta.className = 'px-4 py-1.5 rounded text-sm font-medium transition-colors bg-neon-purple text-white shadow';
            tabSimples.className = 'px-4 py-1.5 rounded text-sm font-medium text-slate-400 hover:text-white transition-colors';
            renderCestas();
        });
    }

    // 2. Busca Global com Debounce
    let searchTimeout;
    inputSearch.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        
        clearTimeout(searchTimeout);
        
        if (query.length < 2) {
            searchResults.classList.add('hidden');
            return;
        }

        searchTimeout = setTimeout(async () => {
            const data = await fetchSearch(query);
            
            searchList.innerHTML = '';
            
            if (data.resultados.length === 0) {
                searchList.innerHTML = '<div class="text-slate-400 italic">Nenhum histórico recente encontrado para esta busca.</div>';
            } else {
                data.resultados.forEach((res, idx) => {
                    const isCheapest = idx === 0;
                    
                    const row = `
                        <div class="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg ${isCheapest ? 'bg-neon-green/10 border border-neon-green/30' : 'bg-slate-800/50 border border-slate-700/50'}">
                            <div>
                                <div class="font-bold text-white flex items-center gap-2">
                                    ${res.mercado}
                                    ${isCheapest ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-neon-green text-slate-900 uppercase">Mais Barato</span>' : ''}
                                </div>
                                <div class="text-xs text-slate-400 mt-1">${res.produto_str}</div>
                                <div class="text-[10px] text-slate-500 mt-0.5"><i class="fa-regular fa-clock"></i> Último registro: ${res.data}</div>
                            </div>
                            <div class="mt-2 sm:mt-0 text-left sm:text-right">
                                <div class="text-xl font-black ${isCheapest ? 'text-neon-green' : 'text-slate-200'}">${formatCurrency(res.preco_padrao)}</div>
                                <div class="text-xs text-slate-500">por ${res.unidade}</div>
                            </div>
                        </div>
                    `;
                    searchList.innerHTML += row;
                });
            }
            
            searchResults.classList.remove('hidden');
            
        }, 500); // 500ms debounce
    });
}

// =========================================================================
// BANCADA DE LANÇAMENTO (Nova Compra)
// =========================================================================

let itemCounter = 0;

function addNewItemRow() {
    const container = document.getElementById('items-container');
    if (!container) return;
    
    const row = document.createElement('div');
    row.className = 'grid grid-cols-1 md:grid-cols-12 gap-4 items-end bg-slate-900/50 p-4 rounded-xl border border-dark-border relative';
    row.id = `item-row-${itemCounter}`;
    
    row.innerHTML = `
        <div class="md:col-span-6 relative" id="combo-container-${itemCounter}">
            <label class="block text-xs font-medium text-slate-400 mb-1">Produto (Catálogo)</label>
            
            <!-- Hidden input to store real value -->
            <input type="hidden" name="itens[${itemCounter}].produto_id" id="prod-id-${itemCounter}" required>
            
            <!-- Visible Search Input -->
            <input type="text" id="prod-search-${itemCounter}" placeholder="Selecione ou busque..." autocomplete="off"
                   class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neon-blue">
                   
            <!-- Dropdown Results -->
            <ul id="prod-list-${itemCounter}" class="hidden absolute z-50 w-full mt-1 bg-slate-800 border border-slate-700 rounded-lg shadow-xl max-h-60 overflow-y-auto">
            </ul>
        </div>
        
        <div class="md:col-span-2">
            <label class="block text-xs font-medium text-slate-400 mb-1">Preço (R$)</label>
            <input type="number" step="0.01" name="itens[${itemCounter}].preco_pago" required placeholder="0.00"
                   class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neon-blue">
        </div>
        
        <div class="md:col-span-2">
            <label class="block text-xs font-medium text-slate-400 mb-1">Qtd Embalagens</label>
            <input type="number" step="0.001" name="itens[${itemCounter}].quantidade" required value="1"
                   class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neon-blue text-center">
        </div>
        
        <!-- Flags Fast Click -->
        <div class="md:col-span-12 flex flex-wrap gap-x-4 gap-y-2 mt-2 pt-3 border-t border-slate-800">
            <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-neon-blue">
                <input type="checkbox" name="itens[${itemCounter}].is_promocao" class="accent-neon-blue w-4 h-4 rounded"> Promoção
            </label>
            <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-neon-purple">
                <input type="checkbox" name="itens[${itemCounter}].is_cupom" class="accent-neon-purple w-4 h-4 rounded"> Cupom
            </label>
            <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-neon-green">
                <input type="checkbox" name="itens[${itemCounter}].is_fidelidade" class="accent-neon-green w-4 h-4 rounded"> Fidelidade
            </label>
            <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-yellow-400">
                <input type="checkbox" name="itens[${itemCounter}].is_validade_proxima" class="accent-yellow-400 w-4 h-4 rounded"> Vencinho
            </label>
        </div>

        <button type="button" onclick="document.getElementById('item-row-${itemCounter}').remove()" class="absolute top-2 right-2 text-slate-500 hover:text-red-500 transition-colors">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
    `;
    
    container.appendChild(row);
    
    // Inicializa Dropdown Customizado para esta linha
    initCombobox(itemCounter);
    
    itemCounter++;
}

// =========================================================================
// LÓGICA DO COMBOBOX DE PRODUTO
// =========================================================================

// Vamos buscar produtos uma vez e manter em memoria (ou quando precisar atualizar)
window.produtosList = window.produtosList || [];
let fetchProdutosPromise = null;

function carregarProdutosSeNecessario() {
    if (window.produtosList.length > 0) return Promise.resolve(window.produtosList);
    
    if (!fetchProdutosPromise) {
        fetchProdutosPromise = fetchProdutos().then(res => {
            window.produtosList = res || [];
            return window.produtosList;
        });
    }
    return fetchProdutosPromise;
}

// Chama assim que o script carregar
carregarProdutosSeNecessario();

function initCombobox(idx) {
    const searchInput = document.getElementById(`prod-search-${idx}`);
    const hiddenInput = document.getElementById(`prod-id-${idx}`);
    const listEl = document.getElementById(`prod-list-${idx}`);
    const container = document.getElementById(`combo-container-${idx}`);
    
    if (!searchInput) return;

    // Abrir lista quando focar
    searchInput.addEventListener('focus', async () => {
        if (window.produtosList.length === 0) {
            await carregarProdutosSeNecessario();
        }
        renderDropdown(searchInput.value, listEl, hiddenInput, searchInput, idx);
        listEl.classList.remove('hidden');
    });

    // Filtrar ao digitar
    searchInput.addEventListener('input', async (e) => {
        hiddenInput.value = ''; // limpa seleção se alterou
        if (window.produtosList.length === 0) {
            await carregarProdutosSeNecessario();
        }
        renderDropdown(e.target.value, listEl, hiddenInput, searchInput, idx);
        listEl.classList.remove('hidden');
    });

    // Limpar se sair sem selecionar nada (não aceitar texto livre inexistente)
    searchInput.addEventListener('blur', () => {
        // Pequeno atraso para dar tempo de o click no 'li' ser processado
        setTimeout(() => {
            if (!hiddenInput.value) {
                searchInput.value = ''; // Reseta o campo
            }
        }, 200);
    });

    // Fechar ao clicar fora
    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            listEl.classList.add('hidden');
        }
    });
}

function renderDropdown(query, listEl, hiddenInput, searchInput, idx) {
    listEl.innerHTML = '';
    const q = query.toLowerCase();
    
    // Filtrar produtos
    const filtered = window.produtosList.filter(p => {
        const str = `${p.tipo} ${p.subtipo || ''} ${p.marca}`.toLowerCase();
        return str.includes(q);
    }).slice(0, 50); // limite de 50 para não travar
    
    // Renderizar resultados
    filtered.forEach(p => {
        const li = document.createElement('li');
        li.className = 'px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white cursor-pointer border-b border-slate-700/50 last:border-0';
        li.innerHTML = `<strong>${p.tipo}</strong> ${p.subtipo ? p.subtipo : ''} - <span class="text-slate-400">${p.marca} (${p.conteudo_embalagem}${p.unidade_medida})</span>`;
        
        li.addEventListener('click', () => {
            hiddenInput.value = p.id;
            searchInput.value = `${p.tipo} ${p.subtipo || ''} - ${p.marca} (${p.conteudo_embalagem}${p.unidade_medida})`;
            listEl.classList.add('hidden');
        });
        
        listEl.appendChild(li);
    });

    // Adicionar botão de cadastro (Sempre no final)
    const addLi = document.createElement('li');
    addLi.className = 'px-3 py-2 text-sm text-neon-blue font-bold bg-slate-900/50 hover:bg-slate-700 cursor-pointer flex items-center gap-2 sticky bottom-0';
    addLi.innerHTML = `<i class="fa-solid fa-plus"></i> Cadastrar "${query}"`;
    addLi.addEventListener('click', () => {
        listEl.classList.add('hidden');
        abrirModalProduto(query, idx);
    });
    listEl.appendChild(addLi);
}

// =========================================================================
// MODAL DE CADASTRO RÁPIDO DE PRODUTO
// =========================================================================

let linhaSendoEditada = null;

function abrirModalProduto(textoDigitado, idxRow) {
    linhaSendoEditada = idxRow;
    const modal = document.getElementById('modal-produto');
    const form = document.getElementById('form-quick-produto');
    
    if (!modal) return;
    
    form.reset();
    
    // Preenche o tipo inicial com o que ele estava tentando buscar
    document.getElementById('quick-tipo').value = textoDigitado;
    
    modal.classList.remove('hidden');
    document.getElementById('quick-tipo').focus();
}

function fecharModalProduto() {
    const modal = document.getElementById('modal-produto');
    if (modal) modal.classList.add('hidden');
    linhaSendoEditada = null;
}

// Listener para fechar modal no botão e no overlay
document.addEventListener('DOMContentLoaded', () => {
    const btnCancel = document.getElementById('btn-cancel-modal');
    const overlay = document.getElementById('modal-overlay');
    const formQuick = document.getElementById('form-quick-produto');
    
    if (btnCancel) btnCancel.addEventListener('click', fecharModalProduto);
    if (overlay) overlay.addEventListener('click', fecharModalProduto);
    
    if (formQuick) {
        // Impede de submeter o form principal se apertar Enter no modal
        formQuick.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                // Apenas dispara o submit do form-quick-produto
                formQuick.requestSubmit();
            }
        });

        formQuick.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btnSave = document.getElementById('btn-save-modal');
            const originalText = btnSave.innerHTML;
            btnSave.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Salvando...';
            btnSave.disabled = true;

            const payload = {
                tipo: document.getElementById('quick-tipo').value.trim(),
                subtipo: document.getElementById('quick-subtipo').value.trim() || null,
                marca: document.getElementById('quick-marca').value.trim(),
                categoria: document.getElementById('quick-categoria').value.trim(),
                conteudo_embalagem: parseFloat(document.getElementById('quick-conteudo').value),
                unidade_medida: document.getElementById('quick-unidade').value
            };

            try {
                const response = await fetch(`${API_BASE}/produtos/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) throw new Error('Falha ao cadastrar');

                const novoProduto = await response.json();
                
                // Atualiza cache em memória
                window.produtosList.push(novoProduto);

                // Preenche a linha que iniciou o modal
                if (linhaSendoEditada !== null) {
                    const hiddenInput = document.getElementById(`prod-id-${linhaSendoEditada}`);
                    const searchInput = document.getElementById(`prod-search-${linhaSendoEditada}`);
                    
                    if (hiddenInput && searchInput) {
                        hiddenInput.value = novoProduto.id;
                        searchInput.value = `${novoProduto.tipo} ${novoProduto.subtipo || ''} - ${novoProduto.marca} (${novoProduto.conteudo_embalagem}${novoProduto.unidade_medida})`;
                        
                        // Move o foco para o campo de preço
                        const priceInput = document.querySelector(`input[name="itens[${linhaSendoEditada}].preco_pago"]`);
                        if (priceInput) priceInput.focus();
                    }
                }
                
                fecharModalProduto();

            } catch (err) {
                console.error(err);
                alert("Erro ao salvar produto.");
            } finally {
                btnSave.innerHTML = originalText;
                btnSave.disabled = false;
            }
        });
    }
});



async function handleNovaCompraSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const mercado_id = parseInt(form.querySelector('[name="mercado_id"]').value);
    const data = form.querySelector('[name="data"]').value;
    const nfe = form.querySelector('[name="nfe"]')?.value || null;
    const observacoes = form.querySelector('[name="observacoes"]')?.value || null;
    const rows = document.getElementById('items-container').querySelectorAll('.grid');
    const itens = [];
    
    for(let row of rows) {
        const produtoId = parseInt(row.querySelector('[name$=".produto_id"]').value);
        
        if(!produtoId) {
            alert('Selecione um produto para cada item!');
            return;
        }

        itens.push({
            produto_id: produtoId,
            preco_pago: row.querySelector('[name$=".preco_pago"]').value,
            quantidade: row.querySelector('[name$=".quantidade"]').value,
            is_promocao: row.querySelector('[name$=".is_promocao"]').checked,
            is_cupom: row.querySelector('[name$=".is_cupom"]').checked,
            is_fidelidade: row.querySelector('[name$=".is_fidelidade"]').checked,
            is_validade_proxima: row.querySelector('[name$=".is_validade_proxima"]')?.checked || false,
            fonte_dado: "cupom_fiscal"
        });
    }
    
    if (itens.length === 0) return alert("Adicione pelo menos um item!");
    
    try {
        const res = await fetch(`${API_BASE}/compras/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mercado_id, data, nfe, observacoes, itens })
        });
        if (res.ok) {
            alert('Lançamento concluído com sucesso!');
            window.location.href = '/';
        } else {
            alert('Erro: ' + JSON.stringify(await res.json()));
        }
    } catch(e) { alert("Erro de conexão."); }
}

// =========================================================================
// HISTÓRICO
// =========================================================================

async function initHistorico() {
    const tbody = document.getElementById('historico-tbody');
    if(!tbody) return;
    
    const compras = await fetchCompras();
    tbody.innerHTML = '';
    
    if(compras.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="px-6 py-8 text-center text-slate-500">Nenhum registro encontrado.</td></tr>`;
        return;
    }

    compras.forEach(c => {
        c.itens.forEach(i => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-800/30 transition-colors';
            
            let tags = '';
            if(i.is_promocao) tags += `<span class="bg-neon-blue/20 text-neon-blue text-[10px] font-bold px-2 py-1 rounded mx-1 uppercase">Promo</span>`;
            if(i.is_cupom) tags += `<span class="bg-neon-purple/20 text-neon-purple text-[10px] font-bold px-2 py-1 rounded mx-1 uppercase">Cupom</span>`;
            if(i.is_fidelidade) tags += `<span class="bg-neon-green/20 text-neon-green text-[10px] font-bold px-2 py-1 rounded mx-1 uppercase">Fidel.</span>`;
            if(i.is_validade_proxima) tags += `<span class="bg-yellow-500/20 text-yellow-400 text-[10px] font-bold px-2 py-1 rounded mx-1 uppercase">Venc.</span>`;
            
            const pLabel = produtoDisplayName(i.produto);
            
            tr.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">${c.data}</td>
                <td class="px-6 py-4">${c.mercado.nome}</td>
                <td class="px-6 py-4 font-medium text-white">${pLabel}</td>
                <td class="px-6 py-4 text-right text-slate-300">R$ ${parseFloat(i.preco_pago).toFixed(2)}</td>
                <td class="px-6 py-4 text-right">${i.quantidade}</td>
                <td class="px-6 py-4 text-right text-neon-blue font-semibold">R$ ${(parseFloat(i.preco_pago) * parseFloat(i.quantidade)).toFixed(2)}</td>
                <td class="px-6 py-4 text-right text-xs text-slate-400">R$ ${parseFloat(i.preco_por_unidade_padrao).toFixed(2)} / ${i.produto.unidade_medida === 'un' ? 'un' : (i.produto.unidade_medida === 'g' || i.produto.unidade_medida === 'kg' ? 'kg' : 'L')}</td>
                <td class="px-6 py-4 text-center">${tags}</td>
            `;
            tbody.appendChild(tr);
        });
    });
}

// =========================================================================
// CADASTROS (Config)
// =========================================================================

async function handleCadastroMercado(e) {
    e.preventDefault();
    const data = {
        nome: e.target.nome.value,
        tipo: e.target.tipo.value,
        endereco: e.target.endereco?.value || null,
        cidade: e.target.cidade?.value || null,
        estado: e.target.estado?.value?.toUpperCase() || null,
        latitude: e.target.latitude?.value ? parseFloat(e.target.latitude.value) : null,
        longitude: e.target.longitude?.value ? parseFloat(e.target.longitude.value) : null
    };
    try {
        const res = await fetch(`${API_BASE}/mercados/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if(res.ok) {
            alert('Mercado cadastrado!');
            e.target.reset();
            window.location.reload();
        } else {
            alert('Erro: ' + JSON.stringify(await res.json()));
        }
    } catch(err) { alert('Erro de conexão.'); }
}

async function handleCadastroProduto(e) {
    e.preventDefault();
    const data = {
        tipo: e.target.tipo.value,
        subtipo: e.target.subtipo?.value || null,
        marca: e.target.marca.value,
        categoria: e.target.categoria.value,
        conteudo_embalagem: e.target.conteudo_embalagem.value,
        unidade_medida: e.target.unidade_medida.value
    };
    try {
        const res = await fetch(`${API_BASE}/produtos/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if(res.ok) {
            alert('Produto cadastrado!');
            e.target.reset();
            window.location.reload();
        } else {
            alert('Erro: ' + JSON.stringify(await res.json()));
        }
    } catch(err) { alert('Erro de conexão.'); }
}

// =========================================================================
// INICIALIZAÇÃO GERAL
// =========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Tenta init do Dashboard
    initDashboard();
    
    // Tenta init da Bancada
    const btnAddItem = document.getElementById('btn-add-item');
    if (btnAddItem) {
        btnAddItem.addEventListener('click', addNewItemRow);
        addNewItemRow(); // Primeira linha vazia
    }
    const formNovaCompra = document.getElementById('form-nova-compra');
    if (formNovaCompra) formNovaCompra.addEventListener('submit', handleNovaCompraSubmit);
    
    // Tenta init do Historico
    initHistorico();
    
    // Tenta init de Config (Cadastros)
    const formMercado = document.getElementById('form-novo-mercado');
    const formProduto = document.getElementById('form-novo-produto');
    if(formMercado) formMercado.addEventListener('submit', handleCadastroMercado);
    if(formProduto) formProduto.addEventListener('submit', handleCadastroProduto);
});
