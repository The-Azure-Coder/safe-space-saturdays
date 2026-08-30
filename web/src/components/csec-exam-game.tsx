import { useEffect, useRef, useState } from 'react'

export type CsecExamState = {
  phase?: 'paper_one' | 'paper_two' | 'complete'
  deadline_at?: number
  paper_one?: Array<{ question: string; options: string[] }>
  paper_two?: Array<{ id: string; prompt: string; marks: number }>
  answers_one?: Array<Array<number | null>>
  answers_two?: string[][]
  paper_one_scores?: number[]
  paper_two_scores?: number[]
  paper_one_breakdown?: Array<{ question: string; selected: string; correct: string; points: number }>
  grades?: Array<Array<{ points: number; feedback?: string } | null>>
  players?: Array<{ name: string; is_bot?: boolean }>
  seat_index?: number
}

export function CsecExamGame({ state, send }: { state: CsecExamState; send: (action: Record<string, unknown>) => void }) {
  const [questionIndex, setQuestionIndex] = useState(0)
  const [reviewPaperOne, setReviewPaperOne] = useState(false)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [written, setWritten] = useState<Record<string, string>>({})
  const [now, setNow] = useState(() => Date.now() / 1000)
  const autoSubmitted = useRef(false)
  const seat = Number(state.seat_index ?? 0)
  const phase = state.phase ?? 'paper_one'
  const paperOne = state.paper_one ?? []
  const paperTwo = state.paper_two ?? []
  const paperOneAnswers = state.answers_one?.[seat] ?? []
  const paperTwoAnswers = state.answers_two?.[seat] ?? []
  const breakdown = state.paper_one_breakdown ?? []

  useEffect(() => {
    if (phase !== 'paper_two') setReviewPaperOne(false)
  }, [phase])
  useEffect(() => {
    autoSubmitted.current = false
  }, [phase, state.deadline_at])
  useEffect(() => {
    if (phase === 'complete' || !state.deadline_at) return
    const timer = window.setInterval(() => {
      const current = Date.now() / 1000
      setNow(current)
      if (current >= state.deadline_at! && !autoSubmitted.current) {
        autoSubmitted.current = true
        send({ action: 'submit_exam' })
      }
    }, 1000)
    return () => window.clearInterval(timer)
  }, [phase, state.deadline_at])

  const chooseAnswer = (index: number, answer: number) => {
    setAnswers((current) => ({ ...current, [index]: answer }))
    send({ action: 'answer_one', question_index: index, answer })
  }
  const saveWrittenAnswer = (id: string, answer: string) => {
    setWritten((current) => ({ ...current, [id]: answer }))
    send({ action: 'answer_two', question_id: id, answer })
  }
  const question = paperOne[questionIndex]
  const paperOneView = phase === 'paper_one' || reviewPaperOne
  const secondsRemaining = state.deadline_at ? Math.max(0, Math.ceil(state.deadline_at - now)) : 0
  const timerLabel = `${String(Math.floor(secondsRemaining / 3600)).padStart(2, '0')}:${String(Math.floor((secondsRemaining % 3600) / 60)).padStart(2, '0')}:${String(secondsRemaining % 60).padStart(2, '0')}`

  return <section className="mini-game-card csec-exam" aria-label="CSEC IT Mock Exam">
    <div className="csec-exam__header"><div><span className="eyebrow">CSEC IT Mock Exam</span><h2>{phase === 'paper_one' ? 'Paper 1 · Multiple choice' : phase === 'paper_two' ? (reviewPaperOne ? 'Review Paper 1' : 'Paper 2 · Written responses') : 'Exam breakdown'}</h2><p>{phase === 'paper_one' ? 'Move between questions with Previous and Next. Your answers are saved as you go.' : phase === 'paper_two' ? 'Complete Paper 2, or go back to review and change a Paper 1 answer.' : 'Your submitted exam results are shown below.'}</p></div><div className="csec-exam__header-meta">{phase !== 'complete' && <span className={secondsRemaining <= 300 ? 'csec-exam__timer is-urgent' : 'csec-exam__timer'} aria-label={`${timerLabel} remaining`}>{timerLabel}</span>}{phase === 'paper_one' && <span className="csec-exam__progress">{paperOneAnswers.filter((answer) => answer !== null).length}/{paperOne.length}</span>}</div></div>
    {paperOneView && question && <div className="csec-exam__questions"><fieldset className="csec-exam__question"><legend><strong>{questionIndex + 1}.</strong> {question.question}</legend><div className="csec-exam__options">{question.options.map((option, optionIndex) => { const selected = (answers[questionIndex] ?? paperOneAnswers[questionIndex]) === optionIndex; return <label className={selected ? 'csec-exam__option is-selected' : 'csec-exam__option'} key={option}><input type="radio" name={`question-${questionIndex}`} checked={selected} onChange={() => chooseAnswer(questionIndex, optionIndex)} /> <span>{option}</span></label> })}</div></fieldset><div className="csec-exam__navigation"><button className="button button--secondary" type="button" disabled={questionIndex === 0} onClick={() => setQuestionIndex((current) => Math.max(0, current - 1))}>Previous</button><span>Question {questionIndex + 1} of {paperOne.length}</span><button className="button button--secondary" type="button" disabled={questionIndex === paperOne.length - 1} onClick={() => setQuestionIndex((current) => Math.min(paperOne.length - 1, current + 1))}>Next</button></div>{reviewPaperOne && <button className="button button--primary" type="button" onClick={() => setReviewPaperOne(false)}>Back to Paper 2</button>}</div>}
    {phase === 'paper_two' && !reviewPaperOne && <div className="csec-exam__written"><button className="button button--secondary" type="button" onClick={() => setReviewPaperOne(true)}>Review Paper 1</button>{paperTwo.map((item, index) => <label className="csec-exam__written-question" key={item.id}><span><strong>{item.id}.</strong> {item.prompt} <small>{item.marks} mark{item.marks === 1 ? '' : 's'}</small></span><textarea value={written[item.id] ?? paperTwoAnswers[index] ?? ''} onChange={(event) => saveWrittenAnswer(item.id, event.target.value)} rows={5} placeholder="Write your answer here…" /></label>)}<button className="button button--primary" type="button" onClick={() => send({ action: 'submit_exam' })}>Submit exam</button></div>}
    {phase === 'complete' && <div className="csec-exam__complete"><h3>Paper 1: {state.paper_one_scores?.[seat] ?? 0}/{paperOne.length}</h3><div className="csec-exam__breakdown"><h3>Paper 1 breakdown</h3>{breakdown.map((item, index) => <div key={index}><span><strong>{index + 1}.</strong> {item.question}</span><small>{item.points ? 'Correct · 1 point' : `Incorrect · Correct answer: ${item.correct}`}<br />Your answer: {item.selected || 'No answer'}</small></div>)}</div><div className="csec-exam__breakdown"><h3>Paper 2 breakdown</h3>{paperTwo.map((item, index) => { const grade = state.grades?.[seat]?.[index]; return <div key={item.id}><span><strong>{item.id}.</strong> {paperTwoAnswers[index] || 'No response submitted.'}</span><small>{grade ? `${grade.points}/${item.marks} points${grade.feedback ? ` · ${grade.feedback}` : ''}` : `Awaiting Tyrese's grading · ${item.marks} marks available`}</small></div> })}</div></div>}
  </section>
}
