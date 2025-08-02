<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	
	import { getMistakeChats, getSubjectStatistics, toggleMistakeById } from '$lib/apis/chats';
	import { user } from '$lib/stores';
	import { getTimeRange } from '$lib/utils';
	
	import Button from '$lib/components/common/Button.svelte';
	import BookOpen from '$lib/components/icons/BookOpen.svelte';
	import Brain from '$lib/components/icons/Brain.svelte';
	import Tags from '$lib/components/icons/Tags.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let mistakeChats = [];
	let subjectStats = {};
	let loading = false;

	onMount(async () => {
		await loadData();
	});

	const loadData = async () => {
		loading = true;
		try {
			const [mistakesRes, statsRes] = await Promise.all([
				getMistakeChats(localStorage.token),
				getSubjectStatistics(localStorage.token)
			]);
			
			if (mistakesRes) {
				mistakeChats = mistakesRes.map(chat => ({
					...chat,
					time_range: getTimeRange(chat.updated_at)
				}));
			}
			
			if (statsRes) {
				subjectStats = statsRes;
			}
		} catch (error) {
			console.error('Error loading mistake data:', error);
			toast.error('加载错题数据失败');
		} finally {
			loading = false;
		}
	};

	const toggleMistake = async (chatId) => {
		try {
			await toggleMistakeById(localStorage.token, chatId);
			await loadData(); // 重新加载数据
			toast.success('错题状态已更新');
		} catch (error) {
			console.error('Error toggling mistake:', error);
			toast.error('更新失败，请重试');
		}
	};

	const openChat = (chatId) => {
		goto(`/c/${chatId}`);
	};

	// 计算统计数据
	$: totalMistakes = mistakeChats.length;
	$: totalSubjects = Object.keys(subjectStats).length;
	$: mostProblematicSubject = Object.entries(subjectStats)
		.filter(([_, stats]) => stats.mistakes > 0)
		.sort(([,a], [,b]) => b.mistakes - a.mistakes)[0];
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
	<div class="max-w-6xl mx-auto p-6">
		<!-- 页面标题 -->
		<div class="mb-8">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-3">
				<BookOpen class="w-8 h-8 text-red-600" />
				错题本
			</h1>
			<p class="text-gray-600 dark:text-gray-400">
				记录和管理您的错题，帮助巩固学习成果
			</p>
		</div>

		<!-- 统计面板 -->
		<div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
			<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-gray-600 dark:text-gray-400">错题总数</p>
						<p class="text-2xl font-bold text-red-600">{totalMistakes}</p>
					</div>
					<BookOpen class="w-8 h-8 text-red-600" />
				</div>
			</div>

			<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-gray-600 dark:text-gray-400">涉及科目</p>
						<p class="text-2xl font-bold text-blue-600">{totalSubjects}</p>
					</div>
					<Brain class="w-8 h-8 text-blue-600" />
				</div>
			</div>

			<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-gray-600 dark:text-gray-400">最需关注</p>
						<p class="text-lg font-bold text-orange-600">
							{mostProblematicSubject ? mostProblematicSubject[0] : '暂无'}
						</p>
						{#if mostProblematicSubject}
							<p class="text-xs text-gray-500">
								{mostProblematicSubject[1].mistakes} 道错题
							</p>
						{/if}
					</div>
					<ChartBar class="w-8 h-8 text-orange-600" />
				</div>
			</div>

			<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-gray-600 dark:text-gray-400">整体正确率</p>
						<p class="text-2xl font-bold text-green-600">
							{Object.values(subjectStats).reduce((acc, stats) => acc + stats.total, 0) > 0 
								? Math.round((1 - totalMistakes / Object.values(subjectStats).reduce((acc, stats) => acc + stats.total, 0)) * 100)
								: 100}%
						</p>
					</div>
					<ChatBubbles class="w-8 h-8 text-green-600" />
				</div>
			</div>
		</div>

		<!-- 科目统计 -->
		{#if Object.keys(subjectStats).length > 0}
			<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mb-8">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
					<ChartBar class="w-5 h-5" />
					科目错题统计
				</h2>
				
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
					{#each Object.entries(subjectStats) as [subject, stats]}
						<div class="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
							<div class="flex items-center justify-between mb-2">
								<h3 class="font-medium text-gray-900 dark:text-white">{subject}</h3>
								<span class="text-sm text-gray-500 dark:text-gray-400">
									{stats.mistakes}/{stats.total}
								</span>
							</div>
							
							<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-2">
								<div 
									class="bg-red-600 h-2 rounded-full transition-all duration-300"
									style="width: {stats.total > 0 ? (stats.mistakes / stats.total) * 100 : 0}%"
								></div>
							</div>
							
							<div class="flex items-center justify-between text-sm">
								<span class="text-gray-600 dark:text-gray-400">
									错误率: {stats.total > 0 ? Math.round((stats.mistakes / stats.total) * 100) : 0}%
								</span>
								<span class="text-blue-600 dark:text-blue-400">
									{stats.knowledge_points.length} 个知识点
								</span>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- 错题列表 -->
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
				<BookOpen class="w-5 h-5" />
				错题列表 ({totalMistakes})
			</h2>
			
			{#if loading}
				<div class="flex items-center justify-center py-12">
					<Spinner class="w-8 h-8" />
					<span class="ml-2 text-gray-600 dark:text-gray-400">加载中...</span>
				</div>
			{:else if mistakeChats.length === 0}
				<div class="text-center py-12">
					<BookOpen class="w-16 h-16 mx-auto text-gray-400 mb-4" />
					<p class="text-gray-600 dark:text-gray-400 text-lg">暂无错题记录</p>
					<p class="text-gray-500 dark:text-gray-500 text-sm mt-2">开始学习并标记错题吧！</p>
				</div>
			{:else}
				<div class="space-y-4">
					{#each mistakeChats as chat}
						<div 
							class="border border-red-200 dark:border-red-800 rounded-lg p-4 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
						>
							<div class="flex items-start justify-between">
								<button 
									type="button"
									class="flex-1 min-w-0 text-left focus:outline-none focus:ring-2 focus:ring-red-500 rounded p-1"
									on:click={() => openChat(chat.id)}
								>
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
										
										<span class="inline-flex items-center px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded-md text-xs">
											错题
										</span>
									</div>
								</button>
								
								<div class="ml-4 flex items-center gap-2">
									<Tooltip content="移出错题本">
										<Button
											variant="outline"
											size="sm"
											class="text-red-600 border-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
											on:click={() => toggleMistake(chat.id)}
										>
											<XMark class="w-4 h-4" />
										</Button>
									</Tooltip>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>