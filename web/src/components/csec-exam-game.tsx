import { useState } from 'react'

export type CsecExamState = {
  phase?: 'paper_one' | 'paper_two' | 'complete'
  question_index?: number
  paper_one?: Array<{ question: string; options: string[] }>
  paper_two?: Array<{ id: string; prompt: string; marks: number }>
  answers_one?: Array<Array<number | null>>
  answers_two?: string[][]
  paper_one_scores?: number[]
  paper_two_scores?: number[]
  grades?: Array<Array<{ points: number; feedback?: string } | null>>
  players?: Array<{ name: string; is_bot?: boolean }>
  seat_index?: number
}

export function CsecExamGame({
  state,
  send,
}: {
  state: CsecExamState
  send: (action: Record<string, unknown>) => void
}) {
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [written, setWritten] = useState<Record<string, string>>({})
  const [grades, setGrades] = useState<Record<string, { points: number; feedback: string }>>({})
  const seat = Number(state.seat_index ?? 0)
  const paperOne = state.paper_one ?? []
  const paperTwo = state.paper_two ?? []
  const phase = state.phase ?? 'paper_one'
  const paperOneAnswers = state.answers_one?.[seat] ?? []
  const paperTwoAnswers = state.answers_two?.[seat] ?? []
  const isTyrese = state.players?.[seat]?.name.trim().toLowerCase() === 'tyrese'

  const chooseAnswer = (questionIndex: number, answer: number) => {
    setAnswers((current) => ({ ...current, [questionIndex]: answer }))
    send({ action: 'answer_one', question_index: questionIndex, answer })
  }
  const saveWrittenAnswer = (questionId: string, answer: string) => {
    setWritten((current) => ({ ...current, [questionId]: answer }))
    send({ action: 'answer_two', question_id: questionId, answer })
  }
  const submit = () => send({ action: 'submit_exam' })

  return <section className="mini-game-card csec-exam" aria-label="CSEC IT Mock Exam">
    <div className="csec-exam__header">
      <div><span className="eyebrow">CSEC IT Mock Exam</span><h2>{phase === 'paper_one' ? 'Paper 1 · Multiple choice' : phase === 'paper_two' ? 'Paper 2 · Written responses' : 'Exam submitted'}</h2><p>{phase === 'paper_one' ? 'Choose the best answer for every question. Your score is calculated automatically.' : phase === 'paper_two' ? 'Write clear, complete responses. Tyrese can review and grade Paper 2.' : 'Your submission is saved for review.'}</p></div>
      {phase === 'paper_one' && <span className="csec-exam__progress">{paperOneAnswers.filter((answer) => answer !== null).length}/{paperOne.length}</span>}
    </div>
    {phase === 'paper_one' && <div className="csec-exam__questions">{paperOne.map((item, index) => <fieldset className="csec-exam__question" key={index}><legend><strong>{index + 1}.</strong> {item.question}</legend><div className="csec-exam__options">{item.options.map((option, optionIndex) => { const selected = (answers[index] ?? paperOneAnswers[index]) === optionIndex; return <label className={selected ? 'csec-exam__option is-selected' : 'csec-exam__option'} key={option}><input type="radio" name={`question-${index}`} checked={selected} onChange={() => chooseAnswer(index, optionIndex)} /> <span>{option}</span></label> })}</div></fieldset>)}</div>}
    {phase === 'paper_two' && <div className="csec-exam__written">{paperTwo.map((item) => <label className="csec-exam__written-question" key={item.id}><span><strong>{item.id}.</strong> {item.prompt} <small>{item.marks} mark{item.marks === 1 ? '' : 's'}</small></span><textarea value={written[item.id] ?? paperTwoAnswers[paperTwo.findIndex((question) => question.id === item.id)] ?? ''} onChange={(event) => saveWrittenAnswer(item.id, event.target.value)} rows={5} placeholder="Write your answer here…" /></label>)}<button className="button button--primary" type="button" onClick={submit}>Submit exam</button></div>}
    {phase === 'complete' && <div className="csec-exam__complete"><h3>Paper 1 score: {state.paper_one_scores?.[seat] ?? 0}/{paperOne.length}</h3><p>Paper 2 responses are ready for review.</p>{isTyrese && <div className="csec-exam__grading"><h3>Paper 2 grading</h3>{paperTwo.map((item, index) => { const key = item.id; const grade = grades[key] ?? { points: state.grades?.[seat]?.[index]?.points ?? 0, feedback: state.grades?.[seat]?.[index]?.feedback ?? '' }; return <div className="csec-exam__grade" key={key}><strong>{item.id} · {item.prompt}</strong><p>{paperTwoAnswers[index] || 'No response submitted.'}</p><label>Points (0–{item.marks})<input type="number" min="0" max={item.marks} value={grade.points} onChange={(event) => setGrades((current) => ({ ...current, [key]: { ...grade, points: Math.max(0, Math.min(item.marks, Number(event.target.value) || 0)) } }))} /></label><label>Feedback<textarea value={grade.feedback} onChange={(event) => setGrades((current) => ({ ...current, [key]: { ...grade, feedback: event.target.value } }))} rows={3} /></label><button className="button button--secondary button--small" type="button" onClick={() => send({ action: 'grade_two', target_player: seat, question_id: key, points: grade.points, feedback: grade.feedback })}>Save grade</button></div> })}</div>}</div>}
  </section>
}
