import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useResearch } from '../context/ResearchContext';
import { Download, Share2, FileText, Globe, Calendar, Lightbulb } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

const ReportPage: React.FC = () => {
  const { state } = useResearch();
  const [isExporting, setIsExporting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const [report, setReport] = useState<any>(null);

  // 基于后端数据生成研究报告
  useEffect(() => {
    const generateReport = async () => {
      try {
        if (state.status === 'completed' && state.researchSummary) {
          // 直接使用后端返回的researchSummary内容
          const reportData = {
            id: state.planId,
            title: `关于"${state.researchTopic}"的研究报告`,
            content: state.researchSummary, // 直接使用后端生成的Markdown内容
            status: state.status,
            created_at: new Date().toISOString(),
          };
          
          setReport(reportData);
        } else {
          setReport(null);
        }
      } catch (error) {
        console.error('生成报告失败:', error);
        setReport(null);
      } finally {
        setIsLoading(false);
      }
    };

    generateReport();
  }, [state.status, state.researchSummary, state.stepResults, state.planId, state.researchTopic]);

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

  if (!report || state.status !== 'completed') {
    return (
      <div className="max-w-4xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-white/80 backdrop-blur-sm rounded-xl p-8 card-shadow"
        >
          <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-4">
            {state.status === 'completed' ? '报告生成中...' : '研究尚未完成'}
          </p>
          <p className="text-sm text-gray-500">
            {state.status === 'completed' 
              ? '正在准备最终报告' 
              : '请先完成研究过程以查看报告'}
          </p>
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-center space-x-3 p-4 bg-gray-50 rounded-xl">
            <Calendar className="h-5 w-5 text-gray-500" />
            <div>
              <p className="text-sm text-gray-600">生成时间</p>
              <p className="font-semibold text-gray-800">{new Date(report.created_at).toLocaleDateString()}</p>
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
          <div className="text-gray-700 leading-relaxed">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={{
                h1: ({ children }) => <h1 className="text-3xl font-bold text-gray-900 mb-6">{children}</h1>,
                h2: ({ children }) => <h2 className="text-2xl font-bold text-gray-800 mb-4 mt-8">{children}</h2>,
                h3: ({ children }) => <h3 className="text-xl font-semibold text-gray-800 mb-3 mt-6">{children}</h3>,
                p: ({ children }) => <p className="text-gray-700 leading-relaxed mb-4">{children}</p>,
                ul: ({ children }) => <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside text-gray-700 mb-4 space-y-2">{children}</ol>,
                li: ({ children }) => <li className="text-gray-700">{children}</li>,
                blockquote: ({ children }) => <blockquote className="border-l-4 border-primary-500 pl-4 italic text-gray-600 my-4">{children}</blockquote>,
                code: ({ children, ...props }) => 
                  props.className?.includes('language') ? 
                    <code className="block bg-gray-100 p-3 rounded-lg text-sm font-mono overflow-x-auto my-4">{children}</code> :
                    <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">{children}</code>,
                pre: ({ children }) => <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto my-4">{children}</pre>,
                strong: ({ children }) => <strong className="font-bold text-gray-900">{children}</strong>,
                em: ({ children }) => <em className="italic text-gray-700">{children}</em>,
              }}
            >
              {report.content}
            </ReactMarkdown>
          </div>

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