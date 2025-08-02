<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	
	import { summarizeChatById, updateChatSummaryById } from '$lib/apis/chats';
	import { user } from '$lib/stores';
	
	import Modal from '../common/Modal.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tags from '../icons/Tags.svelte';
	import BookOpen from '../icons/BookOpen.svelte';
	import Brain from '../icons/Brain.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let show = false;
	export let chatId = '';
	export let existingSummary = null;

	let loading = false;
	let summaryData = {
		subject: '',
		knowledge_points: [],
		summary: '',
		tags: []
	};
	
	let newKnowledgePoint = '';
	let newTag = '';

	const generateSummary = async () => {
		if (!chatId) return;
		
		loading = true;
		try {
			const result = await summarizeChatById(localStorage.token, chatId);
			if (result) {
				summaryData = {
					...result,
					tags: existingSummary?.tags || []
				};
				toast.success('聊天总结生成成功！');
			}
		} catch (error) {
			console.error('Error generating summary:', error);
			toast.error('生成总结失败，请重试');
		} finally {
			loading = false;
		}
	};

	const saveSummary = async () => {
		if (!chatId) return;
		
		loading = true;
		try {
			const result = await updateChatSummaryById(localStorage.token, chatId, {
				subject: summaryData.subject,
				knowledge_points: summaryData.knowledge_points,
				tags: summaryData.tags
			});
			
			if (result) {
				toast.success('聊天信息更新成功！');
				dispatch('updated', summaryData);
				show = false;
			}
		} catch (error) {
			console.error('Error saving summary:', error);
			toast.error('保存失败，请重试');
		} finally {
			loading = false;
		}
	};

	const addKnowledgePoint = () => {
		if (newKnowledgePoint.trim() && !summaryData.knowledge_points.includes(newKnowledgePoint.trim())) {
			summaryData.knowledge_points = [...summaryData.knowledge_points, newKnowledgePoint.trim()];
			newKnowledgePoint = '';
		}
	};

	const removeKnowledgePoint = (index) => {
		summaryData.knowledge_points = summaryData.knowledge_points.filter((_, i) => i !== index);
	};

	const addTag = () => {
		if (newTag.trim() && !summaryData.tags.includes(newTag.trim())) {
			summaryData.tags = [...summaryData.tags, newTag.trim()];
			newTag = '';
		}
	};

	const removeTag = (index) => {
		summaryData.tags = summaryData.tags.filter((_, i) => i !== index);
	};

	const resetForm = () => {
		summaryData = {
			subject: existingSummary?.subject || '',
			knowledge_points: existingSummary?.knowledge_points || [],
			summary: existingSummary?.summary || '',
			tags: existingSummary?.tags || []
		};
	};

	$: if (show && existingSummary) {
		resetForm();
	}
</script>

<Modal bind:show size="lg">
	<div slot="title" class="flex items-center gap-3">
		<Brain />
		<div>智能总结与分类</div>
	</div>

	<div slot="content" class="space-y-4">
		{#if !summaryData.subject && !loading}
			<div class="text-center py-6">
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					使用AI智能分析聊天内容，自动提取科目分类和知识点
				</p>
				<button
					type="button"
					class="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-md transition-colors flex items-center"
					on:click={generateSummary}
				>
					<Brain class="w-4 h-4 mr-2" />
					生成智能总结
				</button>
			</div>
		{:else}
			<div class="space-y-4">
				<!-- 科目分类 -->
				<div>
					<label class="flex items-center gap-2 text-sm font-medium mb-2">
						<BookOpen class="w-4 h-4" />
						科目分类
					</label>
					<select
						bind:value={summaryData.subject}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
					>
						<option value="">请选择科目</option>
						<option value="数学">数学</option>
						<option value="物理">物理</option>
						<option value="化学">化学</option>
						<option value="语文">语文</option>
						<option value="英语">英语</option>
						<option value="历史">历史</option>
						<option value="地理">地理</option>
						<option value="生物">生物</option>
						<option value="政治">政治</option>
						<option value="计算机科学">计算机科学</option>
						<option value="通用">通用</option>
					</select>
				</div>

				<!-- 知识点 -->
				<div>
					<label class="flex items-center gap-2 text-sm font-medium mb-2">
						<ChevronRight class="w-4 h-4" />
						知识点
					</label>
					<div class="space-y-2">
						<div class="flex gap-2">
							<input
								type="text"
								bind:value={newKnowledgePoint}
								placeholder="添加知识点..."
								class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
								on:keydown={(e) => {
									if (e.key === 'Enter') {
										e.preventDefault();
										addKnowledgePoint();
									}
								}}
							/>
							<button type="button" class="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors" on:click={addKnowledgePoint}>添加</button>
						</div>
						<div class="flex flex-wrap gap-2">
							{#each summaryData.knowledge_points as point, index}
								<span class="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-md text-sm">
									{point}
									<button
										type="button"
										class="ml-1 text-blue-600 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-100"
										on:click={() => removeKnowledgePoint(index)}
									>
										×
									</button>
								</span>
							{/each}
						</div>
					</div>
				</div>

				<!-- 标签 -->
				<div>
					<label class="flex items-center gap-2 text-sm font-medium mb-2">
						<Tags class="w-4 h-4" />
						标签
					</label>
					<div class="space-y-2">
						<div class="flex gap-2">
							<input
								type="text"
								bind:value={newTag}
								placeholder="添加标签..."
								class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
								on:keydown={(e) => {
									if (e.key === 'Enter') {
										e.preventDefault();
										addTag();
									}
								}}
							/>
							<button type="button" class="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors" on:click={addTag}>添加</button>
						</div>
						<div class="flex flex-wrap gap-2">
							{#each summaryData.tags as tag, index}
								<span class="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-md text-sm">
									{tag}
									<button
										type="button"
										class="ml-1 text-green-600 hover:text-green-800 dark:text-green-300 dark:hover:text-green-100"
										on:click={() => removeTag(index)}
									>
										×
									</button>
								</span>
							{/each}
						</div>
					</div>
				</div>

				<!-- AI总结内容 -->
				{#if summaryData.summary}
					<div>
						<label class="text-sm font-medium mb-2 block">AI总结</label>
						<div class="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
							<p class="text-gray-700 dark:text-gray-300">{summaryData.summary}</p>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<div slot="footer" class="flex justify-between">
		<div class="flex gap-2">
			{#if summaryData.subject}
				<button
					type="button"
					class="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 bg-transparent hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
					on:click={generateSummary}
					disabled={loading}
				>
					{#if loading}
						<Spinner class="w-4 h-4 mr-2" />
					{/if}
					重新生成
				</button>
			{/if}
		</div>
		
		<div class="flex gap-2">
			<button type="button" class="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 bg-transparent hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors" on:click={() => (show = false)}>取消</button>
			{#if summaryData.subject}
				<button
					type="button"
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
					on:click={saveSummary}
					disabled={loading}
				>
					{#if loading}
						<Spinner class="w-4 h-4 mr-2" />
					{/if}
					保存
				</button>
			{/if}
		</div>
	</div>
</Modal>