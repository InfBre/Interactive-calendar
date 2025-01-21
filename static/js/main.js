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
        const monthGrid = document.getElementById(`month-${month}`);
        if (!monthGrid) return;
        
        monthGrid.innerHTML = '';

        // 添加星期头部
        const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
        weekdays.forEach(day => {
            const header = document.createElement('div');
            header.className = 'weekday-header';
            header.textContent = day;
            monthGrid.appendChild(header);
        });

        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1;
        const currentDate = now.getDate();

        // 添加日期单元格
        calendar.forEach(week => {
            week.forEach(day => {
                const cell = document.createElement('div');
                cell.className = 'day-cell';
                
                if (day.day !== '') {
                    cell.textContent = day.day;
                    
                    // 判断日期状态
                    if (currentYear === 2025) {
                        if (month < currentMonth || (month === currentMonth && day.day < currentDate)) {
                            cell.classList.add('past-date');
                        } else {
                            cell.classList.add('future-date');
                        }
                    }
                    
                    if (day.is_today) {
                        cell.classList.add('today');
                    }
                    
                    // 有备忘录的日期添加标记
                    if (day.notes.length > 0) {
                        cell.classList.add('has-note');
                    }

                    // 添加点击事件处理
                    const date = `2025-${String(month).padStart(2, '0')}-${String(day.day).padStart(2, '0')}`;
                    cell.addEventListener('click', () => handleDayClick(date));
                }
                
                monthGrid.appendChild(cell);
            });
        });
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
    window.loadEvents = async function() {
        console.log('Loading events...');
        try {
            const response = await fetch('/get_events');
            if (!response.ok) {
                throw new Error('Failed to load events');
            }

            const events = await response.json();
            console.log('Loaded events:', events);

            // 更新事件列表
            const eventsList = document.getElementById('events-list');
            if (!eventsList) {
                console.error('Events list element not found');
                return;
            }

            eventsList.innerHTML = '';
            events.sort((a, b) => new Date(a.date) - new Date(b.date))
                .forEach(event => {
                    const item = document.createElement('div');
                    item.className = 'list-group-item';
                    item.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-bold">${event.date}</div>
                                <div>${event.title}</div>
                            </div>
                            <button class="btn btn-danger btn-sm" onclick="window.deleteEvent('${event.id}')">
                                删除
                            </button>
                        </div>
                    `;
                    eventsList.appendChild(item);

                    // 添加到倒计时区域
                    addEventToCountdown(event);
                });
        } catch (error) {
            console.error('加载事件失败:', error);
            if (!handleAuthError(error)) {
                alert('加载事件失败: ' + error.message);
            }
        }
    };

    // 添加事件到倒计时区域
    window.addEventToCountdown = function(event) {
        const countdownGrid = document.querySelector('.countdown-grid');
        if (!countdownGrid) {
            console.error('Countdown grid not found');
            return;
        }

        // 检查是否已存在相同日期的倒计时卡片
        const existingCard = countdownGrid.querySelector(`[data-date="${event.date}"]`);
        if (existingCard) {
            return;
        }

        const card = document.createElement('div');
        card.className = 'countdown-card';
        card.innerHTML = `
            <h3 class="countdown-title">${event.title}</h3>
            <div class="countdown-days" data-date="${event.date}"></div>
            <div class="countdown-date">${event.date}</div>
        `;
        countdownGrid.appendChild(card);
        updateCountdownCard(card);
    };

    // 删除事件
    window.deleteEvent = async function(eventId) {
        console.log('Deleting event:', eventId);
        if (confirm('确定要删除这个事件吗？')) {
            try {
                const response = await fetch('/delete_event', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ id: eventId })
                });

                if (!response.ok) {
                    throw new Error('Failed to delete event');
                }

                const data = await response.json();
                if (data.success) {
                    // 重新加载事件列表
                    await loadEvents();
                } else {
                    throw new Error(data.error || '删除失败');
                }
            } catch (error) {
                console.error('Error deleting event:', error);
                if (!handleAuthError(error)) {
                    alert('删除事件失败: ' + error.message);
                }
            }
        }
    };

    // 加载备忘录
    window.loadNotes = async function() {
        console.log('Loading notes...');
        try {
            const response = await fetch('/api/notes');
            if (!response.ok) {
                throw new Error('Failed to load notes');
            }
            
            const data = await response.json();
            const notes = data.notes || {};
            
            // 更新备忘录列表
            const notesList = document.getElementById('notesList');
            if (!notesList) {
                console.error('Notes list element not found');
                return;
            }
            
            notesList.innerHTML = '';
            Object.entries(notes)
                .sort(([dateA], [dateB]) => new Date(dateB) - new Date(dateA))
                .forEach(([date, content]) => {
                    const item = document.createElement('div');
                    item.className = 'list-group-item';
                    item.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="mb-0">${date}</h6>
                            <div>
                                <button class="btn btn-primary btn-sm me-2" onclick="window.editNote('${date}', this)">编辑</button>
                                <button class="btn btn-danger btn-sm" onclick="window.deleteNote('${date}')">删除</button>
                            </div>
                        </div>
                        <div class="note-content">${content}</div>
                        <div class="note-edit" style="display: none;">
                            <textarea class="form-control mb-2">${content}</textarea>
                            <div class="d-flex justify-content-end gap-2">
                                <button class="btn btn-secondary btn-sm" onclick="window.cancelEdit(this)">取消</button>
                                <button class="btn btn-success btn-sm" onclick="window.saveEdit('${date}', this)">保存</button>
                            </div>
                        </div>
                    `;
                    notesList.appendChild(item);
                });
        } catch (error) {
            console.error('加载备忘录失败:', error);
            if (!handleAuthError(error)) {
                alert('加载备忘录失败: ' + error.message);
            }
        }
    };

    // 编辑备忘录
    window.editNote = function(date, button) {
        console.log('Editing note for date:', date);
        const item = button.closest('.list-group-item');
        const noteContent = item.querySelector('.note-content');
        const noteEdit = item.querySelector('.note-edit');
        const actionButtons = button.closest('.d-flex');
        
        if (noteContent && noteEdit && actionButtons) {
            noteContent.style.display = 'none';
            noteEdit.style.display = 'block';
            actionButtons.style.display = 'none';
        } else {
            console.error('Required elements not found');
        }
    };

    // 取消编辑
    window.cancelEdit = function(button) {
        console.log('Canceling edit');
        const item = button.closest('.list-group-item');
        const noteContent = item.querySelector('.note-content');
        const noteEdit = item.querySelector('.note-edit');
        const actionButtons = item.querySelector('.d-flex.justify-content-between .d-flex');
        
        if (noteContent && noteEdit && actionButtons) {
            noteContent.style.display = 'block';
            noteEdit.style.display = 'none';
            actionButtons.style.display = 'block';
        } else {
            console.error('Required elements not found');
        }
    };

    // 保存编辑
    window.saveEdit = async function(date, button) {
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
                const noteEdit = item.querySelector('.note-edit');
                const actionButtons = item.querySelector('.d-flex.justify-content-between .d-flex');
                
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
            if (!handleAuthError(error)) {
                alert('保存备忘录失败: ' + error.message);
            }
        }
    };

    // 删除备忘录
    window.deleteNote = async function(date) {
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
                if (!handleAuthError(error)) {
                    alert('删除备忘录失败: ' + error.message);
                }
            }
        }
    };

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
                if (!handleAuthError(error)) {
                    alert('保存事件失败: ' + error.message);
                }
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
                if (!handleAuthError(error)) {
                    alert('保存备忘录失败: ' + error.message);
                }
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
        updateClock(); // 启动时钟
        await initCalendar();
        await loadNotes();  // 加载备忘录列表
        await loadEvents(); // 加载事件列表
        updateCountdowns();
        
        // 设置定时器
        setInterval(updateYearProgress, 60000);
        setInterval(updateCountdowns, 60000); // 每分钟更新一次倒计时
    }

    // 启动初始化
    initialize();
});
