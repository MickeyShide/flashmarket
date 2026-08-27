import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled React error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6 text-text-main font-sans">
          <div className="bg-white border border-border-color rounded-lg p-8 max-w-md w-full text-center space-y-4 shadow-sm">
            <div className="w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto text-xl font-black">
              !
            </div>
            <h2 className="text-base font-black uppercase tracking-wider">
              Что-то пошло не так
            </h2>
            <p className="text-xs text-gray-600 font-medium">
              Произошла непредвиденная ошибка интерфейса. Мы уже работаем над её устранением.
            </p>
            {this.state.error?.message && (
              <div className="text-[11px] font-mono text-gray-500 bg-gray-100 p-2.5 rounded text-left overflow-x-auto break-all">
                {this.state.error.message}
              </div>
            )}
            <button
              onClick={this.handleReset}
              className="w-full bg-black text-white py-3 px-6 text-xs font-black uppercase tracking-wider rounded hover:bg-gray-900 cursor-pointer transition-colors"
            >
              Вернуться на главную
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
