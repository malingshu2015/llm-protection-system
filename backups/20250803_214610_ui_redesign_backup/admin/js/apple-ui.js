/**
 * 苹果风格的大模型防火墙界面交互脚本
 */

document.addEventListener('DOMContentLoaded', function() {
  // 侧边栏切换
  const sidebarToggle = document.querySelector('.navbar-menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function() {
      sidebar.classList.toggle('active');
    });
    
    // 点击侧边栏外部区域关闭侧边栏（在移动设备上）
    document.addEventListener('click', function(event) {
      const isClickInside = sidebar.contains(event.target) || sidebarToggle.contains(event.target);
      
      if (!isClickInside && sidebar.classList.contains('active') && window.innerWidth <= 992) {
        sidebar.classList.remove('active');
      }
    });
  }
  
  // 模态框功能
  const modalTriggers = document.querySelectorAll('[data-modal-target]');
  const modalCloseButtons = document.querySelectorAll('.modal-close, [data-modal-close]');
  
  modalTriggers.forEach(trigger => {
    trigger.addEventListener('click', function() {
      const modalId = this.getAttribute('data-modal-target');
      const modal = document.getElementById(modalId);
      
      if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
      }
    });
  });
  
  modalCloseButtons.forEach(button => {
    button.addEventListener('click', function() {
      const modal = this.closest('.modal-backdrop');
      
      if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
      }
    });
  });
  
  // 点击模态框背景关闭模态框
  document.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal-backdrop')) {
      event.target.classList.remove('show');
      document.body.style.overflow = '';
    }
  });
  
  // 表格行悬停效果
  const tableRows = document.querySelectorAll('table tbody tr');
  
  tableRows.forEach(row => {
    row.addEventListener('mouseenter', function() {
      this.classList.add('hover');
    });
    
    row.addEventListener('mouseleave', function() {
      this.classList.remove('hover');
    });
  });
  
  // 卡片悬停效果
  const cards = document.querySelectorAll('.card, .stat-card, .model-item, .model-library-item, .event-card');
  
  cards.forEach(card => {
    card.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-5px)';
      this.style.boxShadow = 'var(--apple-shadow-md)';
    });
    
    card.addEventListener('mouseleave', function() {
      this.style.transform = '';
      this.style.boxShadow = '';
    });
  });
  
  // 按钮点击效果
  const buttons = document.querySelectorAll('.button');
  
  buttons.forEach(button => {
    button.addEventListener('mousedown', function() {
      this.style.transform = 'scale(0.98)';
    });
    
    button.addEventListener('mouseup', function() {
      this.style.transform = '';
    });
    
    button.addEventListener('mouseleave', function() {
      this.style.transform = '';
    });
  });
  
  // 表单验证
  const forms = document.querySelectorAll('form');
  
  forms.forEach(form => {
    form.addEventListener('submit', function(event) {
      let isValid = true;
      const requiredInputs = form.querySelectorAll('[required]');
      
      requiredInputs.forEach(input => {
        if (!input.value.trim()) {
          isValid = false;
          input.classList.add('is-invalid');
          
          // 创建错误消息
          const errorMessage = document.createElement('div');
          errorMessage.className = 'invalid-feedback';
          errorMessage.textContent = '此字段是必填的';
          
          // 如果还没有错误消息，则添加
          if (!input.nextElementSibling || !input.nextElementSibling.classList.contains('invalid-feedback')) {
            input.parentNode.insertBefore(errorMessage, input.nextSibling);
          }
        } else {
          input.classList.remove('is-invalid');
          
          // 移除错误消息
          if (input.nextElementSibling && input.nextElementSibling.classList.contains('invalid-feedback')) {
            input.nextElementSibling.remove();
          }
        }
      });
      
      if (!isValid) {
        event.preventDefault();
      }
    });
  });
  
  // 暗色模式切换
  const darkModeToggle = document.querySelector('#dark-mode-toggle');
  
  if (darkModeToggle) {
    // 检查用户偏好
    const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const storedTheme = localStorage.getItem('theme');
    
    // 根据用户偏好或存储的主题设置初始状态
    if (storedTheme === 'dark' || (!storedTheme && prefersDarkMode)) {
      document.body.classList.add('dark-mode');
      darkModeToggle.checked = true;
    }
    
    darkModeToggle.addEventListener('change', function() {
      if (this.checked) {
        document.body.classList.add('dark-mode');
        localStorage.setItem('theme', 'dark');
      } else {
        document.body.classList.remove('dark-mode');
        localStorage.setItem('theme', 'light');
      }
    });
  }
  
  // 添加页面过渡动画
  document.body.classList.add('fade-in');
  
  // 添加内容元素的动画
  const contentElements = document.querySelectorAll('.card, .stat-card, .model-item, .event-card');
  
  contentElements.forEach((element, index) => {
    // 延迟添加动画类，创建级联效果
    setTimeout(() => {
      element.classList.add('slide-in-left');
    }, 100 + (index * 50));
  });
});
