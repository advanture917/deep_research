import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useResearch } from '../context/ResearchContext';
import { Download, Share2, FileText, Globe, Calendar, Lightbulb } from 'lucide-react';

const ReportPage: React.FC = () => {
  const { state } = useResearch();
  const [isExporting, setIsExporting] = useState(false);

  const [report, setReport] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 获取研究报告
  React.useEffect(() => {
    const fetchReport = async () => {
      if (state.currentPlan) {
        try {
          const response = await fetch(`http://localhost:8000/api/research/report/${state.currentPlan.id}`);
          if (response.ok) {
            const reportData = await response.json();
            setReport(reportData);
          }
        } catch (error) {
          console.error('获取报告失败:', error);
        } finally {
          setIsLoading(false);
        }
      } else {
        setIsLoading(false);
      }
    };

    fetchReport();
  }, [state.currentPlan]);

  const handleExportPDF = async () => {
    setIsExporting(true);
    // 模拟PDF导出（实际使用后端API）
    setTimeout(() => {
      if (report) {
        const blob = new Blob([report.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `research-report-${Date.now()}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
      setIsExporting(false);
    }, 2000);
  };

  const handleExportMarkdown = () => {
    if (report) {
      const blob = new Blob([report.content], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `research-report-${Date.now()}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `关于"${state.researchTopic}"的研究报告`,
          text: '查看这份由AI生成的深度研究报告',
          url: window.location.href,
        });
      } catch (err) {
        console.log('分享取消');
      }
    } else {
      // 复制到剪贴板
      navigator.clipboard.writeText(window.location.href);
      alert('链接已复制到剪贴板');
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-white/80 backdrop-blur-sm rounded-xl p-8 card-shadow"
        >
          <div className="loading-spinner mx-auto mb-4"></div>
          <p className="text-gray-600">正在生成报告...</p>
        </motion.div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="max-w-4xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-white/80 backdrop-blur-sm rounded-xl p-8 card-shadow"
        >
          <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-4">暂无报告数据</p>
          <p className="text-sm text-gray-500">请先完成研究过程</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 card-shadow mb-6"
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">研究报告</h1>
            <p className="text-gray-600">关于"{state.researchTopic}"的深度研究分析</p>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={handleShare}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-100 hover:bg-primary-200 text-primary-700 rounded-lg transition-all duration-200"
            >
              <Share2 className="h-4 w-4" />
              <span>分享</span>
            </button>
            <button
              onClick={handleExportMarkdown}
              className="flex items-center space-x-2 px-4 py-2 bg-secondary-100 hover:bg-secondary-200 text-secondary-700 rounded-lg transition-all duration-200"
            >
              <FileText className="h-4 w-4" />
              <span>导出Markdown</span>
            </button>
            <button
              onClick={handleExportPDF}
              disabled={isExporting}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                isExporting
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'btn-primary'
              }`}
            >
              {isExporting ? (
                <>
                  <div className="loading-spinner h-4 w-4"></div>
                  <span>导出中...</span>
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  <span>导出报告</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Report Metadata */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-3 p-4 bg-gray-50 rounded-xl">
            <Calendar className="h-5 w-5 text-gray-500" />
            <div>
              <p className="text-sm text-gray-600">生成时间</p>
              <p className="font-semibold text-gray-800">{new Date(report.created_at).toLocaleDateString()}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3 p-4 bg-gray-50 rounded-xl">
            <FileText className="h-5 w-5 text-gray-500" />
            <div>
              <p className="text-sm text-gray-600">研究步骤</p>
              <p className="font-semibold text-gray-800">{report.steps.length} 个</p>
            </div>
          </div>
          <div className="flex items-center space-x-3 p-4 bg-gray-50 rounded-xl">
            <Globe className="h-5 w-5 text-gray-500" />
            <div>
              <p className="text-sm text-gray-600">研究状态</p>
              <p className="font-semibold text-gray-800">{report.status}</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Report Content */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 card-shadow"
      >
        <div className="prose prose-lg max-w-none">
          <div className="text-gray-700 leading-relaxed whitespace-pre-wrap">
            {report.content}
          </div>
          
          {/* Research Steps */}
          {report.steps && report.steps.length > 0 && (
            <div className="mt-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">详细研究过程</h2>
              {report.steps.map((step: any, index: number) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="mb-8 p-6 bg-gray-50 rounded-xl border border-gray-200"
                >
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-8 h-8 bg-primary-500 text-white rounded-full flex items-center justify-center font-semibold text-sm">
                      {index + 1}
                    </div>
                    <h3 className="text-xl font-semibold text-gray-800">{step.title}</h3>
                  </div>
                  
                  <div className="mb-4">
                    <p className="text-gray-700 leading-relaxed">{step.content}</p>
                  </div>

                  {step.sources && step.sources.length > 0 && (
                    <div>
                      <h4 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                        <Lightbulb className="h-5 w-5 text-accent-500 mr-2" />
                        参考资料
                      </h4>
                      <div className="space-y-2">
                        {step.sources.map((source: any, sourceIndex: number) => (
                          <div key={sourceIndex} className="flex items-start space-x-3 p-3 bg-white rounded-lg border border-gray-100">
                            <div className="w-2 h-2 bg-primary-500 rounded-full mt-2"></div>
                            <div className="flex-1">
                              <h5 className="font-medium text-gray-800">{source.title}</h5>
                              <p className="text-sm text-gray-600 mt-1">{source.snippet}</p>
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-primary-600 hover:text-primary-700 underline"
                              >
                                查看详情 →
                              </a>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          )}

          <div className="text-center text-sm text-gray-500 border-t border-gray-200 pt-6 mt-8">
            <p>本报告由AI深度研究系统生成，仅供参考</p>
            <p className="mt-1">生成时间: {new Date().toLocaleString()}</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default ReportPage;