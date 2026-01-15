// Progress tracking and auto-redirect functionality

const PROGRESS_STEPS = {
    CONSENT: 'consent',
    TUTORIAL: 'tutorial',
    EVALUATION: 'evaluation',
    SURVEY: 'survey',
    PRIZE: 'prize',
    COMPLETE: 'complete'
};

function getCurrentProgress() {
    return localStorage.getItem('current_step') || PROGRESS_STEPS.CONSENT;
}

function setCurrentProgress(step, additionalData = {}) {
    localStorage.setItem('current_step', step);
    if (additionalData.batch) {
        localStorage.setItem('current_batch', additionalData.batch.toString());
    }
    if (additionalData.page) {
        localStorage.setItem('tutorial_page', additionalData.page.toString());
    }
}

function redirectToCorrectPage() {
    const currentStep = getCurrentProgress();
    const currentPath = window.location.pathname;
    const urlParams = new URLSearchParams(window.location.search);
    
    // Check if user has UUID (has agreed to consent)
    const uuid = localStorage.getItem('chatbot_uuid');
    
    // If no UUID and not on consent page, redirect to consent
    if (!uuid && currentPath !== '/' && currentPath !== '/consent') {
        window.location.href = '/';
        return true;
    }
    
    // If has UUID, check progress and redirect accordingly
    if (uuid) {
        switch(currentStep) {
            case PROGRESS_STEPS.CONSENT:
                // Already agreed, go to tutorial
                if (currentPath === '/' || currentPath === '/consent') {
                    const tutorialPage = localStorage.getItem('tutorial_page') || '1';
                    window.location.href = `/tutorial?page=${tutorialPage}`;
                    return true;
                }
                break;
                
            case PROGRESS_STEPS.TUTORIAL:
                if (currentPath === '/' || currentPath === '/consent') {
                    const tutorialPage = localStorage.getItem('tutorial_page') || '1';
                    window.location.href = `/tutorial?page=${tutorialPage}`;
                    return true;
                }
                if (currentPath.startsWith('/evaluation') || currentPath === '/survey' || currentPath === '/prize') {
                    const tutorialPage = localStorage.getItem('tutorial_page') || '1';
                    window.location.href = `/tutorial?page=${tutorialPage}`;
                    return true;
                }
                break;
                
            case PROGRESS_STEPS.EVALUATION:
                if (currentPath === '/' || currentPath === '/consent' || currentPath === '/tutorial') {
                    const batch = localStorage.getItem('current_batch') || '1';
                    window.location.href = `/evaluation?batch=${batch}`;
                    return true;
                }
                if (currentPath === '/survey' || currentPath === '/prize') {
                    const batch = localStorage.getItem('current_batch') || '1';
                    window.location.href = `/evaluation?batch=${batch}`;
                    return true;
                }
                // If on evaluation but wrong batch, redirect to correct batch
                if (currentPath.startsWith('/evaluation')) {
                    const savedBatch = localStorage.getItem('current_batch') || '1';
                    const currentBatch = urlParams.get('batch') || '1';
                    if (savedBatch !== currentBatch) {
                        window.location.href = `/evaluation?batch=${savedBatch}`;
                        return true;
                    }
                }
                break;
                
            case PROGRESS_STEPS.SURVEY:
                if (currentPath === '/' || currentPath === '/consent' || currentPath === '/tutorial' || currentPath.startsWith('/evaluation')) {
                    window.location.href = '/survey';
                    return true;
                }
                if (currentPath === '/prize') {
                    window.location.href = '/survey';
                    return true;
                }
                break;
                
            case PROGRESS_STEPS.PRIZE:
                if (currentPath !== '/prize') {
                    const prolificId = urlParams.get('id');
                    window.location.href = `/prize${prolificId ? '?id=' + prolificId : ''}`;
                    return true;
                }
                break;
                
            case PROGRESS_STEPS.COMPLETE:
                // Always redirect to completion page if study is complete
                if (currentPath !== '/complete') {
                    const prolificId = urlParams.get('id');
                    window.location.href = `/complete${prolificId ? '?id=' + prolificId : ''}`;
                    return true;
                }
                break;
        }
    }
    
    return false;
}
