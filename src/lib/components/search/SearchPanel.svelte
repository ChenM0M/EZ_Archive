<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	
	import { getChatStatistics, searchChatsByMetadata } from '$lib/apis/chats';
	import { user } from '$lib/stores';
	import { getTimeRange } from '$lib/utils';
	
	import Search from '$lib/components/icons/Search.svelte';
	import BookOpen from '$lib/components/icons/BookOpen.svelte';
	import Brain from '$lib/components/icons/Brain.svelte';
	import Tags from '$lib/components/icons/Tags.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let statistics = {
		subjects: [],
		knowledge_points: [],
		tags: [],
		total_chats: 0
	};
	
	let searchResults = [];
	let loading = false;
	let searchPerformed = false;
	
	// 搜索条件
	let selectedSubject = '';
	let selectedKnowledgePoints = [];
	let selectedTags = [];
	
	// UI状态
	let showSubjectDropdown = false;
	let showKnowledgePointsDropdown = false;
	let showTagsDropdown = false;

	onMount(async () => {
		await loadStatistics();
	});

	const loadStatistics = async () => {
		try {
			const result = await getChatStatistics(localStorage.token);
			if (result) {
				statistics = result;
			}
		} catch (error) {
			console.error('Error loading statistics:', error);
			toast.error('加载统计数据失败');
		}
	};

	const performSearch = async () => {
		loading = true;
		searchPerformed = true;
		
		try {
			const filters = {};
			
			if (selectedSubject) {
				filters.subject = selectedSubject;
			}
			
			if (selectedKnowledgePoints.length > 0) {
				filters.knowledge_points = selectedKnowledgePoints;
			}
			
			if (selectedTags.length > 0) {
				filters.tags = selectedTags;
			}
			
			const results = await searchChatsByMetadata(localStorage.token, filters);
			
			if (results) {
				searchResults = results.map(chat => ({
					...chat,
					time_range: getTimeRange(chat.updated_at)
				}));
				toast.success(`找到 ${searchResults.length} 条聊天记录`);
			}
		} catch (error) {
			console.error('Error searching chats:', error);
			toast.error('搜索失败，请重试');
		} finally {
			loading = false;
		}
	};

	const clearFilters = () => {
		selectedSubject = '';
		selectedKnowledgePoints = [];
		selectedTags = [];
		searchResults = [];
		searchPerformed = false;
	};

	const removeKnowledgePoint = (kp) => {
		selectedKnowledgePoints = selectedKnowledgePoints.filter(item => item !== kp);
	};

	const removeTag = (tag) => {
		selectedTags = selectedTags.filter(item => item !== tag);
	};

	const addKnowledgePoint = (kp) => {
		if (!selectedKnowledgePoints.includes(kp)) {
			selectedKnowledgePoints = [...selectedKnowledgePoints, kp];
		}
		showKnowledgePointsDropdown = false;
	};

	const addTag = (tag) => {
		if (!selectedTags.includes(tag)) {
			selectedTags = [...selectedTags, tag];
		}
		showTagsDropdown = false;
	};

	const openChat = (chatId) => {
		goto(`/c/${chatId}`);
	};

	$: hasFilters = selectedSubject || selectedKnowledgePoints.length > 0 || selectedTags.length > 0;
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
	<div class="max-w-6xl mx-auto p-6">
		<!-- 页面标题 -->
		<div class="mb-8">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
				学习记录检索
			</h1>
			<p class="text-gray-600 dark:text-gray-400">
				通过科目、知识点和标签查找您的历史聊天记录 
				{#if statistics.total_chats > 0}
					(共 {statistics.total_chats} 条记录)
				{/if}
			</p>
		</div>

		<!-- 搜索条件面板 -->
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mb-6">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
				<Search class="w-5 h-5" />
				搜索条件
			</h2>
			
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
				<!-- 科目选择 -->
				<div class="relative">
					<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						<BookOpen class="w-4 h-4 inline mr-1" />
						科目
					</div>
					<div class="relative">
						<button
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-left flex items-center justify-between"
							on:click={() => showSubjectDropdown = !showSubjectDropdown}
						>
							<span class="text-gray-900 dark:text-gray-100">
								{selectedSubject || '选择科目...'}
							</span>
							<ChevronDown class="w-4 h-4" />
						</button>
						
						{#if showSubjectDropdown}
							<div class="absolute z-10 w-full mt-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg">
								<button
									class="w-full px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100"
									on:click={() => { selectedSubject = ''; showSubjectDropdown = false; }}
								>
									全部科目
								</button>
								{#each statistics.subjects as subject}
									<button
										class="w-full px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100"
										on:click={() => { selectedSubject = subject; showSubjectDropdown = false; }}
									>
										{subject}
									</button>
								{/each}
							</div>
						{/if}
					</div>
				</div>

				<!-- 知识点选择 -->
				<div class="relative">
					<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						<Brain class="w-4 h-4 inline mr-1" />
						知识点
					</div>
					<div class="relative">
						<button
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-left flex items-center justify-between"
							on:click={() => showKnowledgePointsDropdown = !showKnowledgePointsDropdown}
						>
							<span class="text-gray-900 dark:text-gray-100">
								{selectedKnowledgePoints.length > 0 ? `已选择 ${selectedKnowledgePoints.length} 个` : '选择知识点...'}
							</span>
							<ChevronDown class="w-4 h-4" />
						</button>
						
						{#if showKnowledgePointsDropdown}
							<div class="absolute z-10 w-full mt-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-48 overflow-y-auto">
								{#each statistics.knowledge_points as kp}
									<button
										class="w-full px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 {selectedKnowledgePoints.includes(kp) ? 'bg-blue-50 dark:bg-blue-900' : ''}"
										on:click={() => addKnowledgePoint(kp)}
									>
										{kp}
									</button>
								{/each}
							</div>
						{/if}
					</div>
					
					<!-- 已选择的知识点 -->
					{#if selectedKnowledgePoints.length > 0}
						<div class="flex flex-wrap gap-2 mt-2">
							{#each selectedKnowledgePoints as kp}
								<span class="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-md text-sm">
									{kp}
									<button
										type="button"
										class="ml-1 text-blue-600 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-100"
										on:click={() => removeKnowledgePoint(kp)}
									>
										<XMark class="w-3 h-3" />
									</button>
								</span>
							{/each}
						</div>
					{/if}
				</div>

				<!-- 标签选择 -->
				<div class="relative">
					<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						<Tags class="w-4 h-4 inline mr-1" />
						标签
					</div>
					<div class="relative">
						<button
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-left flex items-center justify-between"
							on:click={() => showTagsDropdown = !showTagsDropdown}
						>
							<span class="text-gray-900 dark:text-gray-100">
								{selectedTags.length > 0 ? `已选择 ${selectedTags.length} 个` : '选择标签...'}
							</span>
							<ChevronDown class="w-4 h-4" />
						</button>
						
						{#if showTagsDropdown}
							<div class="absolute z-10 w-full mt-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-48 overflow-y-auto">
								{#each statistics.tags as tag}
									<button
										class="w-full px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 {selectedTags.includes(tag) ? 'bg-green-50 dark:bg-green-900' : ''}"
										on:click={() => addTag(tag)}
									>
										{tag}
									</button>
								{/each}
							</div>
						{/if}
					</div>
					
					<!-- 已选择的标签 -->
					{#if selectedTags.length > 0}
						<div class="flex flex-wrap gap-2 mt-2">
							{#each selectedTags as tag}
								<span class="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-md text-sm">
									{tag}
									<button
										type="button"
										class="ml-1 text-green-600 hover:text-green-800 dark:text-green-300 dark:hover:text-green-100"
										on:click={() => removeTag(tag)}
									>
										<XMark class="w-3 h-3" />
									</button>
								</span>
							{/each}
						</div>
					{/if}
				</div>
			</div>

			<!-- 搜索按钮 -->
			<div class="flex gap-3">
				<button
					type="button"
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={performSearch}
					disabled={loading || !hasFilters}
				>
					{#if loading}
						<Spinner class="w-4 h-4" />
					{:else}
						<Search class="w-4 h-4" />
					{/if}
					搜索
				</button>
				
				{#if hasFilters}
					<button
						type="button"
						class="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 bg-transparent hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors"
						on:click={clearFilters}
					>
						清除条件
					</button>
				{/if}
			</div>
		</div>

		<!-- 搜索结果 -->
		{#if searchPerformed}
			<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
					<ChatBubbles class="w-5 h-5" />
					搜索结果 ({searchResults.length})
				</h2>
				
				{#if loading}
					<div class="flex items-center justify-center py-12">
						<Spinner class="w-8 h-8" />
						<span class="ml-2 text-gray-600 dark:text-gray-400">搜索中...</span>
					</div>
				{:else if searchResults.length === 0}
					<div class="text-center py-12">
						<ChatBubbles class="w-16 h-16 mx-auto text-gray-400 mb-4" />
						<p class="text-gray-600 dark:text-gray-400 text-lg">未找到匹配的聊天记录</p>
						<p class="text-gray-500 dark:text-gray-500 text-sm mt-2">尝试调整搜索条件</p>
					</div>
				{:else}
					<div class="space-y-4">
						{#each searchResults as chat}
							<button 
								type="button"
								class="w-full text-left border border-gray-200 dark:border-gray-600 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
								on:click={() => openChat(chat.id)}
							>
								<div class="flex items-start justify-between">
									<div class="flex-1 min-w-0">
										<h3 class="text-lg font-medium text-gray-900 dark:text-white truncate">
											{chat.title}
										</h3>
										<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
											{chat.time_range}
										</p>
										
										<!-- 元数据 -->
										<div class="flex flex-wrap gap-2 mt-3">
											{#if chat.meta?.subject}
												<span class="inline-flex items-center px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded-md text-xs">
													<BookOpen class="w-3 h-3 mr-1" />
													{chat.meta.subject}
												</span>
											{/if}
											
											{#each (chat.meta?.knowledge_points || []) as kp}
												<span class="inline-flex items-center px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-md text-xs">
													<Brain class="w-3 h-3 mr-1" />
													{kp}
												</span>
											{/each}
											
											{#each (chat.meta?.tags || []) as tag}
												<span class="inline-flex items-center px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-md text-xs">
													<Tags class="w-3 h-3 mr-1" />
													{tag}
												</span>
											{/each}
										</div>
									</div>
								</div>
							</button>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<!-- 点击外部关闭下拉菜单 -->
<svelte:window on:click={() => {
	showSubjectDropdown = false;
	showKnowledgePointsDropdown = false;
	showTagsDropdown = false;
}} />