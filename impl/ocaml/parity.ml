(* Parity checker for the canonical book format.

   Reads R|id|band|balance and F|id|op|inputs|outputs lines, validates the
   references, and prints the weighted depth with the FNV-1a 64 fingerprint
   every other port must agree on. *)

let micro = 1_000_000
let thin_floor = 250 * micro
let fnv_offset = 0xCBF29CE484222325
let fnv_prime = 0x100000001B3
let mask = 0xFFFFFFFFFFFFFFFF

type reserve = { rid : string; band : string; balance : int64 }
type flow = { fid : string; op : string; inputs : string list; outputs : string list }

let weight_micro band =
  match band with
  | "buffer" -> 800_000L
  | "edge" -> 450_000L
  | "sink" -> 200_000L
  | _ -> Int64.of_int micro

let normalise_band band =
  match band with
  | "seed" | "core" | "buffer" | "edge" | "sink" -> band
  | _ -> "core"

let split_list field =
  String.split_on_char ',' field |> List.filter (fun part -> String.length part > 0)

let trim text = String.trim text

let fail message = Error message

let parse text =
  let lines = String.split_on_char '\n' text in
  let rec go number reserves flows = function
    | [] ->
        let all = List.map (fun r -> r.rid) reserves in
        let known = Hashtbl.create 64 in
        List.iter (fun id -> Hashtbl.replace known id ()) all;
        let bad = ref None in
        List.iter
          (fun f ->
            List.iter
              (fun ref ->
                if not (Hashtbl.mem known ref) && !bad = None then
                  bad := Some ("flow " ^ f.fid ^ ": unknown reserve " ^ ref))
              (f.inputs @ f.outputs))
          flows;
        (match !bad with Error_ -> Some (Error (Option.get !bad)) | _ -> None) |> ignore;
        (match !bad with
        | Some message -> Error message
        | None -> Ok (List.rev reserves, List.rev flows))
    | raw :: rest ->
        let line = trim raw in
        if line = "" || line.[0] = '#' then go (number + 1) reserves flows rest
        else
          match String.split_on_char '|' line with
          | [ "R"; rid; band; balance ] ->
              if List.exists (fun r -> r.rid = rid) reserves then
                fail ("line " ^ string_of_int number ^ ": duplicate reserve " ^ rid)
              else (
                match Int64.of_string_opt balance with
                | None -> fail ("line " ^ string_of_int number ^ ": bad balance")
                | Some value ->
                    go (number + 1)
                      ({ rid; band = normalise_band band; balance = value } :: reserves)
                      flows rest)
          | [ "F"; fid; op; ins; outs ] ->
              if List.exists (fun f -> f.fid = fid) flows then
                fail ("line " ^ string_of_int number ^ ": duplicate flow " ^ fid)
              else (
                match split_list outs with
                | [] -> fail ("line " ^ string_of_int number ^ ": flow " ^ fid ^ " credits nothing")
                | outputs ->
                    go (number + 1) reserves
                      ({ fid; op = (if op = "" then "derive" else op); inputs = split_list ins; outputs } :: flows)
                      rest)
          | _ -> fail ("line " ^ string_of_int number ^ ": malformed record")
  in
  go 1 [] [] lines

let fingerprint reserves flows =
  let buffer = Buffer.create 4096 in
  List.iter
    (fun r ->
      Buffer.add_string buffer
        (Printf.sprintf "R|%s|%s|%Ld\n" r.rid r.band r.balance))
    reserves;
  List.iter
    (fun f ->
      Buffer.add_string buffer
        (Printf.sprintf "F|%s|%s|%s|%s\n" f.fid f.op
           (String.concat "," (List.sort compare f.inputs))
           (String.concat "," (List.sort compare f.outputs))))
    flows;
  let payload = Buffer.contents buffer in
  let hash = ref fnv_offset in
  String.iter
    (fun ch ->
      hash := Int64.to_int (Int64.logand (Int64.of_int (Char.code ch)) 0xFFL);
      hash := Int64.to_int (Int64.logand (Int64.mul !hash fnv_prime) mask);
      hash := !hash lxor Char.code ch)
    payload;
  let hash = ref fnv_offset in
  String.iter
    (fun ch ->
      hash := Int64.to_int (Int64.logand (Int64.of_int !hash) mask);
      hash := !hash lxor Char.code ch;
      hash := Int64.to_int (Int64.logand (Int64.mul (Int64.of_int !hash) fnv_prime) mask))
    payload;
  Printf.sprintf "%016Lx" (Int64.of_int !hash)

let () =
  if Array.length Sys.argv < 2 then (
    print_endline "usage: parity <book.txt>";
    exit 2);
  let path = Sys.argv.(1) in
  let channel = open_in_bin path in
  let length = in_channel_length channel in
  let text = really_input_string channel length in
  close_in channel;
  match parse text with
  | Error message ->
      Printf.eprintf "error: %s\n" message;
      exit 3
  | Ok (reserves, flows) ->
      let reserves = List.sort (fun a b -> compare a.rid b.rid) reserves in
      let flows = List.sort (fun a b -> compare a.fid b.fid) flows in
      let raw = List.fold_left (fun acc r -> Int64.add acc r.balance) 0L reserves in
      let depth =
        List.fold_left
          (fun acc r -> Int64.add acc (Int64.div (Int64.mul r.balance (weight_micro r.band)) (Int64.of_int micro)))
          0L reserves
      in
      let thin = List.length (List.filter (fun r -> r.balance > 0L && r.balance < Int64.of_int thin_floor) reserves) in
      let debited = Hashtbl.create 16 in
      List.iter
        (fun f -> if f.inputs <> [] then List.iter (fun out -> Hashtbl.replace debited out ()) f.outputs)
        flows;
      let origins = List.filter_map (fun r -> if Hashtbl.mem debited r.rid then None else Some r.rid) reserves in
      let score = if raw > 0L then Int64.to_float depth /. Int64.to_float raw else 0.0 in
      Printf.printf "reserves %d\n" (List.length reserves);
      Printf.printf "flows %d\n" (List.length flows);
      Printf.printf "raw %Ld\n" raw;
      Printf.printf "depth %Ld\n" depth;
      Printf.printf "score %.4f\n" score;
      Printf.printf "thin %d\n" thin;
      Printf.printf "origins %s\n" (String.concat "," origins);
      Printf.printf "fingerprint %s\n" (fingerprint reserves flows)
