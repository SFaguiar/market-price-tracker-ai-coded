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
// DASHBOARD
// =========================================================================

async function initDashboard() {
    const ctxHistory = document.getElementById('chartTendencia');
    if (!ctxHistory) return;
    
    const compras = await fetchCompras();
    if (compras.length === 0) return;
    
    // Processamento de dados
    const gastosPorDia = {};
    let totalGasto = 0;
    
    // Para cálculo de Outliers
    const historicoPrecosProduto = {}; 
    
    compras.forEach(compra => {
        const dataStr = compra.data; 
        let gastoCompra = 0;
        
        compra.itens.forEach(item => {
            const gastoItem = parseFloat(item.preco_pago) * parseFloat(item.quantidade);
            gastoCompra += gastoItem;
            
            // Registrando preço por unidade padrão para média
            const pId = item.produto.id;
            const pLabel = produtoDisplayName(item.produto);
            if(!historicoPrecosProduto[pId]) {
                historicoPrecosProduto[pId] = { nome: pLabel, precos: [] };
            }
            historicoPrecosProduto[pId].precos.push({
                data: dataStr,
                preco_padrao: parseFloat(item.preco_por_unidade_padrao),
                mercado: compra.mercado.nome,
                is_promocao: item.is_promocao
            });
        });
        
        if (!gastosPorDia[dataStr]) gastosPorDia[dataStr] = 0;
        gastosPorDia[dataStr] += gastoCompra;
        
        // Se a data for no mês atual
        const hoje = new Date();
        const dataCompra = new Date(dataStr);
        if (dataCompra.getMonth() === hoje.getMonth() && dataCompra.getFullYear() === hoje.getFullYear()) {
            totalGasto += gastoCompra;
        }
    });
    
    // Atualizar KPI
    const totalGastoEl = document.getElementById('kpi-gasto-mes');
    if (totalGastoEl) {
        totalGastoEl.textContent = formatCurrency(totalGasto);
    }
    
    // Ordenar datas
    const sortedDates = Object.keys(gastosPorDia).sort();
    const historyData = sortedDates.map(date => gastosPorDia[date]);
    
    // Gráfico de Tendência (Limitado a 3 meses)
    new Chart(ctxHistory, {
        type: 'line',
        data: {
            labels: sortedDates.slice(-90), // Últimos 90 dias
            datasets: [{
                label: 'Gasto Diário (R$)',
                data: historyData.slice(-90),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#0f172a',
                pointBorderColor: '#3b82f6',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }
        }
    });

    // Detectar Outliers (+15% da média)
    const outliersList = document.getElementById('outliers-list');
    const outliersEmpty = document.getElementById('outliers-empty');
    if(outliersList) {
        outliersList.innerHTML = ''; // Limpar skeletons
        let hasOutlier = false;

        Object.values(historicoPrecosProduto).forEach(prod => {
            if(prod.precos.length > 2) {
                // Média de todos exceto o último
                const historicoAntigo = prod.precos.slice(0, -1);
                const soma = historicoAntigo.reduce((acc, curr) => acc + curr.preco_padrao, 0);
                const media = soma / historicoAntigo.length;
                
                const ultimaCompra = prod.precos[prod.precos.length - 1];
                const diferencaPerc = ((ultimaCompra.preco_padrao - media) / media) * 100;

                if(diferencaPerc > 15) {
                    hasOutlier = true;
                    outliersList.innerHTML += `
                        <div class="bg-slate-800/50 border border-red-500/30 rounded-lg p-3">
                            <div class="text-sm font-semibold text-white mb-1">${prod.nome}</div>
                            <div class="flex justify-between items-center text-xs">
                                <span class="text-slate-400">${ultimaCompra.data} no ${ultimaCompra.mercado}</span>
                                <span class="text-red-400 font-bold">+${diferencaPerc.toFixed(1)}% acima da média</span>
                            </div>
                        </div>
                    `;
                }
            }
        });

        if(!hasOutlier && outliersEmpty) {
            outliersEmpty.classList.remove('hidden');
        }
    }
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
        <div class="md:col-span-6">
            <label class="block text-xs font-medium text-slate-400 mb-1">Produto (Catálogo)</label>
            <select name="itens[${itemCounter}].produto_id" required
                   class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neon-blue">
                <option value="">Selecione um produto...</option>
            </select>
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
        <div class="md:col-span-12 flex gap-4 mt-2 pt-3 border-t border-slate-800">
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
    
    // Carregar opções do select de produto via API
    const selectEl = row.querySelector(`[name="itens[${itemCounter}].produto_id"]`);
    populateProdutoSelect(selectEl);
    
    itemCounter++;
}

async function populateProdutoSelect(selectEl) {
    const produtos = await fetchProdutos();
    produtos.forEach(p => {
        const option = document.createElement('option');
        option.value = p.id;
        option.textContent = produtoDisplayName(p);
        selectEl.appendChild(option);
    });
}

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
