document.addEventListener('DOMContentLoaded', function() {
    let selectedDate = null;
    
    // 更新年度进度
    function updateYearProgress() {
        const now = new Date();
        const start = new Date(2025, 0, 1);
        const end = new Date(2025, 11, 31, 23, 59, 59);
        const progress = ((now - start) / (end - start)) * 100;
        
        document.getElementById('yearProgressBar').style.width = progress + '%';
        document.getElementById('yearProgress').textContent = progress.toFixed(1) + '%';
    }

    // 获取月份数据
    async function fetchMonthData(year, month) {
        try {
            const response = await fetch(`/api/calendar?year=${year}&month=${month}`);
            const data = await response.json();
            renderMonth(month, data.calendar);
        } catch (error) {
            console.error('获取月份数据失败:', error);
        }
    }

    // 计算月份进度
    function updateMonthProgress() {
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1;
        const currentDate = now.getDate();

        for (let month = 1; month <= 12; month++) {
            const daysInMonth = new Date(2025, month, 0).getDate();
            let progress = 0;

            if (currentYear === 2025 && currentMonth === month) {
                progress = (currentDate / daysInMonth * 100).toFixed(1);
            } else if (currentYear === 2025 && currentMonth > month) {
                progress = 100;
            }

            const progressElement = document.getElementById(`progress-${month}`);
            if (progressElement) {
                progressElement.textContent = progress + '%';
            }
        }
    }

    // 渲染月份
    function renderMonth(month, calendar) {
        const monthContainer = document.getElementById(`month-${month}`);
        if (!monthContainer) return;

        // 清空现有内容
        monthContainer.innerHTML = '';

        // 创建日历表格
        const table = document.createElement('table');
        table.className = 'calendar-table';

        // 添加表头
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        ['日', '一', '二', '三', '四', '五', '六'].forEach(day => {
            const th = document.createElement('th');
            th.textContent = day;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // 添加日期
        const tbody = document.createElement('tbody');
        let currentRow;

        calendar.forEach((week, weekIndex) => {
            currentRow = document.createElement('tr');
            week.forEach((day, dayIndex) => {
                const td = document.createElement('td');
                if (day !== 0) {
                    td.textContent = day;
                    td.addEventListener('click', () => {
                        const date = `2025-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                        handleDayClick(date);
                    });
                }
                currentRow.appendChild(td);
            });
            tbody.appendChild(currentRow);
        });

        table.appendChild(tbody);
        monthContainer.appendChild(table);
    }

    // 处理日期点击
    function handleDayClick(date) {
        selectedDate = date;
        // 切换到备忘录标签页并设置日期
        document.getElementById('nav-memo-tab').click();
        document.getElementById('memoDate').value = date;
        document.getElementById('memoContent').focus();
    }

    // 加载事件列表
    async function loadEvents() {
        try {
            const response = await fetch('/api/events');
            if (!response.ok) {
                throw new Error('Failed to fetch events');
            }
            const events = await response.json();
            
            // 清空现有事件列表
            const eventsList = document.getElementById('eventsList');
            if (!eventsList) {
                console.error('Events list container not found');
                return;
            }
            eventsList.innerHTML = '';
            
            // 按日期排序事件
            events.sort((a, b) => new Date(a.date) - new Date(b.date));
            
            // 添加事件到列表
            events.forEach(event => {
                const eventItem = document.createElement('div');
                eventItem.className = 'list-group-item';
                eventItem.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${event.title}</h6>
                            <small class="text-muted">${event.date}</small>
                        </div>
                        <button class="btn btn-danger btn-sm" onclick="deleteEvent('${event._id}')">
                            删除
                        </button>
                    </div>
                `;
                eventsList.appendChild(eventItem);
                
                // 添加到倒计时区域
                addEventToCountdown(event);
            });
        } catch (error) {
            console.error('Error loading events:', error);
        }
    }

    // 加载备忘录
    async function loadNotes() {
        try {
            const response = await fetch('/api/notes');
            if (!response.ok) {
                throw new Error('Failed to fetch notes');
            }
            const notes = await response.json();
            
            // 清空现有备忘录列表
            const notesList = document.getElementById('notesList');
            if (!notesList) {
                console.error('Notes list container not found');
                return;
            }
            notesList.innerHTML = '';
            
            // 将对象转换为数组并按日期排序
            const notesArray = Object.entries(notes).map(([date, content]) => ({date, content}));
            notesArray.sort((a, b) => new Date(a.date) - new Date(b.date));
            
            // 添加备忘录到列表
            notesArray.forEach(({date, content}) => {
                const noteItem = document.createElement('div');
                noteItem.className = 'list-group-item';
                noteItem.innerHTML = `
                    <div class="note-item" data-date="${date}">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">${date}</h6>
                                <p class="mb-1 note-content">${content}</p>
                            </div>
                            <div class="btn-group">
                                <button class="btn btn-primary btn-sm edit-note" onclick="editNote('${date}', this)">
                                    编辑
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="deleteNote('${date}')">
                                    删除
                                </button>
                            </div>
                        </div>
                        <div class="edit-form" style="display: none;">
                            <textarea class="form-control mb-2">${content}</textarea>
                            <div class="btn-group">
                                <button class="btn btn-success btn-sm" onclick="saveEdit('${date}', this)">
                                    保存
                                </button>
                                <button class="btn btn-secondary btn-sm" onclick="cancelEdit(this)">
                                    取消
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                notesList.appendChild(noteItem);
            });
        } catch (error) {
            console.error('Error loading notes:', error);
        }
    }

    // 编辑备忘录
    function editNote(date, button) {
        console.log('Editing note for date:', date);
        const item = button.closest('.list-group-item');
        const noteContent = item.querySelector('.note-content');
        const noteEdit = item.querySelector('.edit-form');
        const actionButtons = button.closest('.btn-group');
        
        if (noteContent && noteEdit && actionButtons) {
            noteContent.style.display = 'none';
            noteEdit.style.display = 'block';
            actionButtons.style.display = 'none';
        } else {
            console.error('Required elements not found');
        }
    }

    // 取消编辑
    function cancelEdit(button) {
        console.log('Canceling edit');
        const item = button.closest('.list-group-item');
        const noteContent = item.querySelector('.note-content');
        const noteEdit = item.querySelector('.edit-form');
        const actionButtons = item.querySelector('.btn-group');
        
        if (noteContent && noteEdit && actionButtons) {
            noteContent.style.display = 'block';
            noteEdit.style.display = 'none';
            actionButtons.style.display = 'block';
        } else {
            console.error('Required elements not found');
        }
    }

    // 保存编辑
    async function saveEdit(date, button) {
        console.log('Saving edit for date:', date);
        const item = button.closest('.list-group-item');
        const textarea = item.querySelector('textarea');
        
        if (!textarea) {
            console.error('Textarea not found');
            return;
        }

        const content = textarea.value;
        
        try {
            const response = await fetch('/api/notes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    date: date,
                    note: content
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save note');
            }

            const data = await response.json();
            if (data.success) {
                // 更新显示
                const noteContent = item.querySelector('.note-content');
                const noteEdit = item.querySelector('.edit-form');
                const actionButtons = item.querySelector('.btn-group');
                
                if (noteContent && noteEdit && actionButtons) {
                    noteContent.textContent = content;
                    noteContent.style.display = 'block';
                    noteEdit.style.display = 'none';
                    actionButtons.style.display = 'block';
                } else {
                    console.error('Required elements not found');
                }
            } else {
                throw new Error(data.error || '保存失败');
            }
        } catch (error) {
            console.error('Error saving note:', error);
        }
    }

    // 删除备忘录
    async function deleteNote(date) {
        console.log('Deleting note for date:', date);
        if (confirm('确定要删除这条备忘录吗？')) {
            try {
                const response = await fetch(`/api/notes?date=${date}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error('Failed to delete note');
                }

                const data = await response.json();
                if (data.success) {
                    // 重新加载备忘录列表
                    await loadNotes();
                } else {
                    throw new Error(data.error || '删除失败');
                }
            } catch (error) {
                console.error('Error deleting note:', error);
            }
        }
    }

    // 初始化事件表单
    const eventForm = document.getElementById('eventForm');
    if (eventForm) {
        console.log('Event form found, setting up submit handler');
        eventForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Event form submitted');

            const eventData = {
                id: Date.now().toString(),  // 使用时间戳作为唯一ID
                title: document.getElementById('eventDescription').value,
                date: document.getElementById('eventDate').value,
            };

            console.log('Created event data:', eventData);
            try {
                const response = await fetch('/save_event', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(eventData)
                });

                if (!response.ok) {
                    throw new Error('Failed to save event');
                }

                const data = await response.json();
                if (data.success) {
                    // 清空表单
                    this.reset();
                    // 重新加载事件列表
                    await loadEvents();
                    alert('事件添加成功！');
                } else {
                    throw new Error(data.error || '保存失败');
                }
            } catch (error) {
                console.error('Error saving event:', error);
            }
        });
    } else {
        console.error('Event form not found');
    }

    // 初始化备忘录表单
    const memoForm = document.getElementById('memoForm');
    if (memoForm) {
        console.log('Memo form found, setting up submit handler');
        memoForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Memo form submitted');

            const date = document.getElementById('memoDate').value;
            const content = document.getElementById('memoContent').value;

            console.log('Saving memo:', { date, content });
            try {
                const response = await fetch('/api/notes', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        date: date,
                        note: content
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to save memo');
                }

                const data = await response.json();
                if (data.success) {
                    // 清空表单
                    this.reset();
                    // 重新加载备忘录列表
                    await loadNotes();
                    alert('备忘录添加成功！');
                } else {
                    throw new Error(data.error || '保存失败');
                }
            } catch (error) {
                console.error('Error saving memo:', error);
            }
        });
    } else {
        console.error('Memo form not found');
    }

    // 格式化倒计时显示
    function formatCountdown(timeDiff) {
        if (timeDiff < 0) {
            return { text: '已过期', status: 'expired' };
        }
        
        const days = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
        let status = '';
        
        if (days === 0) {
            return { text: '今天', status: 'today' };
        } else {
            if (days <= 3) {
                status = 'upcoming';
            } else {
                status = 'normal';
            }
            return { text: `${days}天`, status };
        }
    }

    // 更新倒计时卡片
    function updateCountdownCard(card) {
        const date = card.querySelector('.countdown-days').dataset.date;
        const eventDate = new Date(date);
        const now = new Date();
        const timeDiff = eventDate - now;
        
        const { text, status } = formatCountdown(timeDiff);
        
        card.className = `countdown-card ${status}`;
        card.querySelector('.countdown-days').textContent = text;
    }

    // 更新倒计时显示
    function updateCountdowns() {
        document.querySelectorAll('.countdown-card').forEach(updateCountdownCard);
    }

    // 更新时钟显示
    function updateClock() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const date = String(now.getDate()).padStart(2, '0');
        const day = ['日', '一', '二', '三', '四', '五', '六'][now.getDay()];

        document.getElementById('clock').textContent = `${hours}:${minutes}:${seconds}`;
        document.getElementById('date').textContent = `${year}年${month}月${date}日 星期${day}`;
        
        // 为 motto 文字添加动画
        const motto = document.querySelector('.motto');
        if (motto && !motto.querySelector('span')) {
            const text = motto.textContent.trim();
            const words = text.split(' ');
            motto.textContent = '';
            words.forEach((word, index) => {
                const span = document.createElement('span');
                span.textContent = word;
                motto.appendChild(span);
                if (index < words.length - 1) {
                    motto.appendChild(document.createTextNode(' '));
                }
            });
        }

        setTimeout(updateClock, 1000);
    }

    // 初始化
    async function initialize() {
        console.log('Initializing calendar app...');
        updateYearProgress();
        updateMonthProgress();
        updateClock();
        
        // 初始化所有月份的日历
        for (let month = 1; month <= 12; month++) {
            fetchMonthData(2025, month);
        }
        
        // 加载事件和备忘录
        loadEvents();
        loadNotes();
        
        // 设置定时器
        setInterval(updateClock, 1000);
        setInterval(updateCountdowns, 1000);
        setInterval(updateYearProgress, 60000);
        setInterval(updateMonthProgress, 60000);
    }

    // 启动初始化
    initialize();
});
